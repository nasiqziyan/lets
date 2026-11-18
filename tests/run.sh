#!/usr/bin/env bash
# End-to-end tests for LETS's command, guard and setup. Uses a throwaway HOME; never touches the real one.
# Usage: tests/run.sh   (needs git, python3 3.11+, GNU sed for the fixtures (macOS: brew install gnu-sed) and
# `npm install` run once in the repo, for OpenSpec)
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(cd "$(mktemp -d)" && pwd -P)"  # the real path: on macOS the temp folder is behind a link
export HOME="$T/home" LETS_TEST_HOME="$T/home" XDG_CONFIG_HOME="$T/home/.config" XDG_STATE_HOME="$T/home/.local/state" \
       XDG_DATA_HOME="$T/home/.local/share" XDG_CACHE_HOME="$T/home/.cache" CODEX_HOME="$T/home/.codex"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t OPENSPEC_TELEMETRY=0
export LETS_GUARD_STRICT=1 LETS_NO_UPDATE_CHECK=1  # a crashing guard fails the tests; no network
export PATH="$REPO/node_modules/.bin:$PATH"
mkdir -p "$HOME"
git config --global init.defaultBranch main
git config --global commit.gpgsign false
pass=0; fail=0
ok()   { pass=$((pass+1)); echo "  ok   $1"; }
bad()  { fail=$((fail+1)); echo "  FAIL $1"; }
check(){ if eval "$2" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi; }
LETS="$REPO/bin/lets"
[ -x "$REPO/node_modules/.bin/openspec" ] || { echo "OpenSpec isn't installed here: run npm install in $REPO"; exit 1; }
# agent "<command>" [tool]: what the guard decides for a call an agent makes from the current directory (0 allow, 2 block)
agent() {
  local tool="${2:-Bash}" key="command"
  [ "$tool" != Bash ] && [ "$tool" != apply_patch ] && key="file_path"
  python3 -c 'import json,sys; print(json.dumps({"tool_name":sys.argv[1],"tool_input":{sys.argv[2]:sys.argv[3]},"cwd":sys.argv[4]}))' "$tool" "$key" "$1" "$PWD" \
    | python3 "$REPO/agent-hooks/guard.py" >/dev/null 2>&1; echo $?
}
# no eval here, so any quoting in the command reaches the guard exactly as written
blocked() { local r; r=$(agent "$1" "${2:-}"); if [ "$r" = 2 ]; then ok "blocks: $1"; else bad "blocks: $1 (exit $r)"; fi; }
allowed() { local r; r=$(agent "$1" "${2:-}"); if [ "$r" = 0 ]; then ok "allows: $1"; else bad "allows: $1 (exit $r)"; fi; }
stage() { mkdir -p "$(dirname "$1")"; printf '%s\n' "$2" > "$1"; git add "$1"; }
reset() { git reset -q --hard; git clean -qfd; }

echo "the command"
check "lets --version prints the package's version" "\"$LETS\" --version | grep -qx \"LETS \$(python3 -c \"import json;print(json.load(open('$REPO/package.json'))['version'])\")\""
check "lets --help ends with where to get help" "\"$LETS\" --help | grep -q 'lets doctor'"
check "an unknown command fails with usage" "! \"$LETS\" nonsense"
check "the npm package ships everything Codex needs to add the plugin (its marketplace manifest)" "(cd '$REPO' && npm pack --dry-run --json 2>/dev/null) | grep -q '\"path\": \".agents/plugins/marketplace.json\"'"
check "a Python older than 3.11 is refused with how to install a newer one" "python3 -c 'import sys;sys.version_info=(3,9,0,\"final\",0);sys.argv=[\"x\",\"--version\"];exec(open(\"$REPO/lib/lets/__main__.py\").read())' 2>&1 | grep -q 'apt install'"

echo "install"
mkdir -p "$CODEX_HOME"  # Codex counts as present; its own CLI isn't needed for these checks
mkdir -p "$HOME/.claude/skills" && ln -s /nonexistent/someone-elses-lets "$HOME/.claude/skills/lets"
"$LETS" install --yes >"$T/install.log" 2>&1; rc=$?
check "install refuses, changing nothing, when ~/.claude/skills/lets is someone else's" "[ $rc -ne 0 ] && grep -q 'skills/lets' '$T/install.log' && [ ! -e \$HOME/lets ] && [ \"\$(readlink \$HOME/.claude/skills/lets)\" = /nonexistent/someone-elses-lets ]"
rm "$HOME/.claude/skills/lets"
printf '{\n  // my comment\n  "model": "x"\n}\n' > "$HOME/.claude/settings.json"
"$LETS" install --yes >"$T/install.log" 2>&1; rc=$?
check "install refuses, changing nothing, when settings.json isn't plain JSON" "[ $rc -ne 0 ] && [ ! -e \$HOME/lets ] && grep -q 'my comment' \$HOME/.claude/settings.json"
printf '{"model": "x"}\n' > "$HOME/.claude/settings.json"
printf '# mine\n' > "$HOME/.claude/CLAUDE.md"
"$LETS" install </dev/null >"$T/noyes.log" 2>&1
check "without a terminal or --yes, install shows the changes, makes none, and says how" "grep -q 'Nothing was changed' '$T/noyes.log' && grep -q 'add --yes' '$T/noyes.log' && [ ! -e \$HOME/lets ] && [ \"\$(cat \$HOME/.claude/CLAUDE.md)\" = '# mine' ]"
"$LETS" install --dry-run >"$T/dry.log" 2>&1
check "install --dry-run shows each file's exact change, and makes none" "grep -q 'Dry run: nothing was changed' '$T/dry.log' && grep -q 'CLAUDE.md' '$T/dry.log' && [ ! -e \$HOME/lets ]"
"$LETS" install --yes >"$T/install.log" 2>&1; check "install exits 0" "[ $? -eq 0 ]"
check "install ends with the next step" "grep -q '^Next:' '$T/install.log' && grep -q 'lets setup' '$T/install.log'"
check "~/lets points at the package" "[ \"\$(cd \$HOME/lets && pwd -P)\" = \"$REPO\" ]"
check "the plugin is linked for Claude Code" "[ \"\$(cd \$HOME/.claude/skills/lets && pwd -P)\" = \"$REPO/plugin\" ]"
for s in epic-start epic-resolve epic-overview epic-revise epic-split change-start change-revise change-close patch build review \
         walkthrough ideas learn handoff pickup retro next help add lens; do
  check "command $s" "[ -f \$HOME/.claude/skills/lets/skills/$s/SKILL.md ] && grep -qx 'disable-model-invocation: true' \$HOME/.claude/skills/lets/skills/$s/SKILL.md"
done
check "exactly 21 commands you type" "[ \$(grep -lx 'disable-model-invocation: true' \$HOME/.claude/skills/lets/skills/*/SKILL.md | wc -l) -eq 21 ]"
for h in tdd grilling code-review diagnosing-bugs research prototype domain-modeling codebase-design; do
  check "helper $h stays out of the / menu" "grep -qx 'user-invocable: false' \$HOME/.claude/skills/lets/skills/$h/SKILL.md"
done
for r in architecture security performance api frontend observability browser ci migrate simplify launch constraints wayfinder to-spec to-tickets doubt sources git pr quality; do
  check "reference $r (read by path, not a skill)" "[ -f \$HOME/.claude/skills/lets/refs/$r/SKILL.md ] && [ ! -e \$HOME/.claude/skills/lets/skills/$r ]"
done
check "Addy's checklists ship with the plugin" "[ -f \$HOME/.claude/skills/lets/refs/checklists/security-checklist.md ]"
check "removed commands are gone" "for s in commit-message pr-description questionnaire rephrase setup intake security wizard writing-for-agents; do [ ! -e '$REPO/plugin/skills/'\$s ] || exit 1; done"
check "the rename table gives Matt's text LETS's words" "! grep -qiw 'tickets\\?' '$REPO/plugin/refs/wayfinder/SKILL.md' && grep -q 'prerequisite' '$REPO/plugin/refs/wayfinder/SKILL.md' && grep -q 'Waits on' '$REPO/plugin/refs/to-tickets/SKILL.md'"
check "Matt's vendored text itself is untouched" "grep -q 'ticket' '$REPO/vendor/mattpocock-skills/skills/engineering/wayfinder/SKILL.md'"
check "commands are typed, never started by the agent, in Codex too" "grep -q 'allow_implicit_invocation: false' '$REPO/plugin/skills/build/agents/openai.yaml'"
check "the plugin matches its sources" "python3 '$REPO/scripts/maint.py' check"
check "CLAUDE.md imports the map and the profile, and keeps what was there" "grep -q '@~/lets/AGENTS.md' \$HOME/.claude/CLAUDE.md && grep -q '@$XDG_CONFIG_HOME/lets/profile.md' \$HOME/.claude/CLAUDE.md && grep -qx '# mine' \$HOME/.claude/CLAUDE.md"
check "Codex AGENTS.md holds the map and the profile" "grep -q 'How I work' \$CODEX_HOME/AGENTS.md && grep -q 'My LETS profile' \$CODEX_HOME/AGENTS.md"
check "the profile has every default answer (no terminal: defaults)" "grep -q '^Answer: pair\$' \$XDG_CONFIG_HOME/lets/profile.md && grep -q '^Answer: local' \$XDG_CONFIG_HOME/lets/profile.md && grep -q '^Answer: about 500 words' \$XDG_CONFIG_HOME/lets/profile.md && grep -q '^Answer: one decision at a time' \$XDG_CONFIG_HOME/lets/profile.md && grep -q 'scaffolding' \$XDG_CONFIG_HOME/lets/profile.md"
check "the message-length answer says split, don't squeeze" "grep -q \"Split, don't squeeze\" \$XDG_CONFIG_HOME/lets/profile.md"
check "install keeps AI attribution out of commits and PRs, and keeps your settings" "python3 -c \"import json;d=json.load(open('\$HOME/.claude/settings.json'));assert d['attribution']=={'commit':'','pr':''} and d['includeCoAuthoredBy'] is False and d['model']=='x'\""
check "install offers the status line when you have none (--yes takes it)" "python3 -c \"import json;d=json.load(open('\$HOME/.claude/settings.json'));assert d['statusLine']['command']=='~/lets/bin/lets statusline' and d['statusLine']['refreshInterval']==5\""
check "Codex reads CLAUDE.md as a fallback" "grep -q 'project_doc_fallback_filenames' \$CODEX_HOME/config.toml"
check "the guard and the session-start check come with the plugin, not settings.json" "python3 -c \"import json;h=json.load(open('$REPO/plugin/hooks/hooks.json'))['hooks'];assert h['PreToolUse'][0]['matcher'].startswith('Bash|Edit') and 'guard.sh' in h['PreToolUse'][0]['hooks'][0]['command'] and 'session-start' in h['SessionStart'][0]['hooks'][0]['command']\" && ! grep -q guard \$HOME/.claude/settings.json"
check "Codex gets the guard and the session-start hook" "grep -q 'guard.sh' \$CODEX_HOME/hooks.json && grep -q 'session-start.sh' \$CODEX_HOME/hooks.json"
check "both tools may write learning notes, kept outside the package" "grep -q '$XDG_DATA_HOME/lets/learning' \$HOME/.claude/settings.json && grep -A1 'sandbox_workspace_write' \$CODEX_HOME/config.toml | grep -q '$XDG_DATA_HOME/lets/learning'"
check "install adds no global git ignore" "[ ! -e \$XDG_CONFIG_HOME/git/ignore ]"
check "install backs up what it edits to the state folder, not the settings folder" "grep -rqx '# mine' \$XDG_STATE_HOME/lets/backups && [ ! -e \$XDG_CONFIG_HOME/lets/backups ]"
check "install records the version it wired up" "grep -q '\"installed\"' \$XDG_CONFIG_HOME/lets/config.json"
check "the lets command on ~/.local/bin runs (through its link)" "[ -x \$HOME/.local/bin/lets ] && \$HOME/.local/bin/lets --version | grep -q LETS"
"$LETS" install --yes >/dev/null 2>&1
check "re-running install changes nothing" "[ \$(grep -c 'lets:begin' \$HOME/.claude/CLAUDE.md) -eq 1 ] && ! \"$LETS\" install --dry-run 2>&1 | grep -q 'changes ·'"
printf '{"model": "x", "statusLine": {"type": "command", "command": "my-line.sh"}}\n' > "$T/sl.json"
check "your own status line is never replaced" "python3 -c \"import sys;sys.path.insert(0,'$REPO/lib');from lets import install,paths;import json,shutil;shutil.copy('$T/sl.json',str(paths.P.claude_settings));print(install.ask_statusline(True))\" | grep -qx None"
"$LETS" install --yes >/dev/null 2>&1
SLC="python3 -c \"import json,os;print((json.load(open(os.environ['HOME']+'/.claude/settings.json')).get('statusLine') or {}).get('command',''))\""
check "statusline on asks before replacing your own (no terminal, no --yes: nothing changes)" "! \"$LETS\" statusline on </dev/null && [ \"\$($SLC)\" = my-line.sh ]"
check "statusline on --yes replaces yours, says so, and saves yours" "\"$LETS\" statusline on --yes 2>&1 | tr '\n' ' ' | grep -q 'replaces yours:.*my-line.sh' && [ \"\$($SLC)\" = '~/lets/bin/lets statusline' ] && grep -q my-line.sh \$XDG_CONFIG_HOME/lets/config.json"
check "statusline on again changes nothing" "\"$LETS\" statusline on --yes | grep -q 'already on'"
check "statusline off takes LETS's status line out and puts yours back" "\"$LETS\" statusline off --yes >/dev/null && [ \"\$($SLC)\" = my-line.sh ]"
printf '{"model": "x"}\n' > "$HOME/.claude/settings.json"
check "with no status line of your own, on then off leaves none" "\"$LETS\" statusline on --yes >/dev/null && [ \"\$($SLC)\" = '~/lets/bin/lets statusline' ] && \"$LETS\" statusline off --yes >/dev/null && [ -z \"\$($SLC)\" ]"
cp "$T/sl.json" "$HOME/.claude/settings.json"
check "statusline off leaves your own status line alone" "\"$LETS\" statusline off --yes | grep -q 'yours stays' && [ \"\$($SLC)\" = my-line.sh ]"
check "statusline with no action still prints the line for Claude Code" "echo '{}' | \"$LETS\" statusline >/dev/null"
"$LETS" install --yes >/dev/null 2>&1
TOOLS="python3 -c \"import json,os;print(','.join(json.load(open(os.environ['XDG_CONFIG_HOME']+'/lets/config.json')).get('tools',[])))\""
check "with Claude Code and Codex both found, install --yes sets up both and records it" "[ \"\$($TOOLS)\" = claude,codex ]"
check "install --tools takes only claude and codex" "! \"$LETS\" install --tools claude,cursor --yes 2>&1 | grep -q Traceback && ! \"$LETS\" install --tools cursor --yes >/dev/null 2>&1"
check "lets profile tools needs a terminal, and says what to run instead" "\"$LETS\" profile tools </dev/null 2>&1 | grep -q 'install --tools'"
# switch tools as if picked in a terminal: the question answers Claude Code only, then Both; changes are agreed
SWITCH="python3 -c \"import sys;sys.path.insert(0,'$REPO/lib');from lets import install,ui,changes;ui.interactive=lambda:True;ui.select=lambda *a,**k:sys.argv[1];install.agree=lambda c,cmd,y,d,o=False:changes.agree(c,cmd,True,False);install.cmd_tools()\""
check "profile tools: Claude Code only takes LETS out of Codex, and leaves Claude Code as it is" "$SWITCH claude >/dev/null && [ \"\$($TOOLS)\" = claude ] && ! grep -q guard.sh \$CODEX_HOME/hooks.json && grep -q 'lets:begin' \$HOME/.claude/CLAUDE.md && [ -L \$HOME/.claude/skills/lets ]"
check "doctor says Codex isn't set up by your choice, and doesn't count that as a problem" "\"$LETS\" doctor --yes | grep -q 'Codex: not set up (your choice' && \"$LETS\" doctor --yes | grep -q 'all checks pass'"
check "install leaves out a tool you chose not to use" "\"$LETS\" install --yes >/dev/null 2>&1 && ! grep -q guard.sh \$CODEX_HOME/hooks.json"
check "profile tools: Both puts LETS back in Codex" "$SWITCH both >/dev/null && [ \"\$($TOOLS)\" = claude,codex ] && grep -q guard.sh \$CODEX_HOME/hooks.json"
check "install --tools codex records the choice" "\"$LETS\" install --tools codex --yes >/dev/null 2>&1 && [ \"\$($TOOLS)\" = codex ]"
eval "$SWITCH both" >/dev/null 2>&1
check "back to both, doctor says both are set up" "\"$LETS\" doctor --yes | grep -q 'Codex: set up' && \"$LETS\" doctor --yes | grep -q 'Claude Code: set up'"
mkdir -p "$HOME/.claude/skills/clash-test"; echo x > "$HOME/.claude/skills/clash-test/SKILL.md"
NOPY="$T/no-python"; mkdir -p "$NOPY"; for b in sh grep dirname cat; do ln -sf "$(command -v $b)" "$NOPY/$b"; done
check "without python3 the guard blocks git, gh and glab, and lets the rest through" "echo '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git push\"}}' | PATH='$NOPY' sh '$REPO/agent-hooks/guard.sh'; [ \$? -eq 2 ] && echo '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ls -la\"}}' | PATH='$NOPY' sh '$REPO/agent-hooks/guard.sh'"
check "a guard that crashes blocks the call and says why" "echo 'not json' | LETS_GUARD_STRICT= python3 '$REPO/agent-hooks/guard.py' 2>&1 | grep -q 'internal error'; [ \${PIPESTATUS[1]} -eq 2 ]"
check "the session-start check is silent when all is well" "[ -z \"\$(sh '$REPO/agent-hooks/session-start.sh')\" ]"
python3 -c "import json,os;p=os.environ['XDG_CONFIG_HOME']+'/lets/config.json';d=json.load(open(p));d['installed']='0.9.0';json.dump(d,open(p,'w'))"
check "the session-start check says when LETS changed but wasn't re-wired" "sh '$REPO/agent-hooks/session-start.sh' | grep -q 'lets install'"
"$LETS" install --yes >/dev/null 2>&1
if command -v claude >/dev/null 2>&1; then
  check "Claude Code loads the plugin as lets@skills-dir" "claude plugin list 2>/dev/null | grep -q 'lets@skills-dir'"
fi

echo "profile"
check "lets profile without a terminal lists the answers" "\"$LETS\" profile | grep -q '^length  *Medium'"
check "lets profile <question> takes a unique prefix" "python3 -c \"import sys;sys.path.insert(0,'$REPO/lib');from lets import profile;assert profile.resolve('len')=='length' and profile.resolve('build')=='build'\""
check "an ambiguous or unknown question is refused with the list" "\"$LETS\" profile zzz 2>&1 | grep -q 'The questions:'"
check "changing an answer rewrites only that section and refreshes Codex's copy" "python3 -c \"
import sys;sys.path.insert(0,'$REPO/lib')
from lets import profile,install
have=profile.current();have.pop(profile.choice('length').heading)
profile.write({'length':profile.choice_text('length','short')},have);install.refresh_codex_copy()
assert profile.answer('length')=='short' and profile.answer('build')=='pair'\" && grep -q 'about 250 words' \$CODEX_HOME/AGENTS.md"

check "the profile's AI credit is never by default" "grep -A1 'AI credit in commits' \$XDG_CONFIG_HOME/lets/profile.md | grep -q 'Answer: never'"
CREDIT="python3 -c \"import sys;sys.path.insert(0,'$REPO/lib');from lets import profile,ui;import argparse;ui.interactive=lambda:True;picks=iter(sys.argv[1:]);ui.select=lambda *a,**k:next(picks);ui.text=lambda *a,**k:next(picks);profile.cmd_profile(argparse.Namespace(question='ai-credit'))\""
eval "$CREDIT trailer-pr 'Generated-by: Claude Code'" >/dev/null 2>&1
check "lets profile ai-credit: a trailer and a pull request note, with a preset trailer" "grep -A1 'AI credit in commits' \$XDG_CONFIG_HOME/lets/profile.md | grep -q 'Answer: trailer and PR note: Generated-by: Claude Code'"
eval "$CREDIT trailer custom 'Helped-by: an agent'" >/dev/null 2>&1
check "lets profile ai-credit: your own trailer" "grep -A1 'AI credit in commits' \$XDG_CONFIG_HOME/lets/profile.md | grep -q 'Answer: trailer: Helped-by: an agent'"
eval "$CREDIT never" >/dev/null 2>&1
check "lets profile ai-credit: back to never" "grep -A1 'AI credit in commits' \$XDG_CONFIG_HOME/lets/profile.md | grep -q 'Answer: never'"
check "setup --ai-credit refuses a value it doesn't know" "python3 -c \"import sys;sys.path.insert(0,'$REPO/lib');from lets import setup;from lets.core import LetsError
try: setup.credit_flag('sometimes')
except LetsError: sys.exit(0)
sys.exit(1)\" && python3 -c \"import sys;sys.path.insert(0,'$REPO/lib');from lets import setup;assert setup.credit_flag('trailer')=='trailer:Assisted-by: Claude Code' and setup.credit_flag('profile')=='' and setup.credit_flag('trailer-pr:X-By: y')=='trailer-pr:X-By: y'\""

echo "learning notes"
check "the profile says where learning notes go: LETS's folder by default" "grep -A1 'Learning notes' \$XDG_CONFIG_HOME/lets/profile.md | grep -q \"Answer: LETS's folder\" && grep -q 'saves notes in .*lets/learning' \$XDG_CONFIG_HOME/lets/profile.md"
NOTES="$T/my-notes"; mkdir -p "$NOTES/learning" "$XDG_DATA_HOME/lets/learning"; (cd "$NOTES" && git init -q && git remote add origin https://example.com/notes.git)
echo "# Closures" > "$XDG_DATA_HOME/lets/learning/closures.md"
# pick "a folder of yours" in a terminal: the question answers custom, the folder is typed, the changes are agreed
PICK="python3 -c \"import sys;sys.path.insert(0,'$REPO/lib');from lets import profile,ui,install,changes;ui.interactive=lambda:True;ui.select=lambda *a,**k:sys.argv[1];ui.text=lambda *a,**k:sys.argv[2] if len(sys.argv)>2 else None;install.agree=lambda c,cmd,y,d,o=False:changes.agree(c,cmd,True,False);import argparse;profile.cmd_profile(argparse.Namespace(question='notes'))\""
eval "$PICK custom $NOTES/learning" >"$T/notes.log" 2>&1
check "a notes folder in a git repo: says LETS never commits there, and warns about its remote" "grep -q 'never commits your notes' '$T/notes.log' && grep -q 'has a remote (origin: https://example.com/notes.git)' '$T/notes.log'"
check "your notes folder goes in the profile and in config.json" "profile_notes=\$(python3 -c \"import sys;sys.path.insert(0,'$REPO/lib');from lets import profile;print(profile.answer('notes'))\") && [ \"\$profile_notes\" = custom ] && grep -q 'a folder of mine' \$XDG_CONFIG_HOME/lets/profile.md && grep -q '\"notes\"' \$XDG_CONFIG_HOME/lets/config.json"
check "notes already saved move to the new folder" "[ -f '$NOTES/learning/closures.md' ] && [ ! -f '$XDG_DATA_HOME/lets/learning/closures.md' ]"
check "both tools may write to the new notes folder" "grep -q '$NOTES/learning' \$HOME/.claude/settings.json && grep -q '$NOTES/learning' \$CODEX_HOME/config.toml"
cd "$NOTES"; blocked "git add learning/closures.md"; blocked "git commit -m notes"; blocked "git push"; allowed "git status"; allowed "git log --oneline"
cd "$NOTES/learning"; blocked "git commit -am notes"; cd "$REPO"
blocked "git -C $NOTES commit -m notes"
eval "$PICK off" >/dev/null 2>&1
check "choosing no notes: the profile says so, and no notes folder is added" "grep -A1 'Learning notes' \$XDG_CONFIG_HOME/lets/profile.md | grep -q 'Answer: none' && python3 -c \"import sys;sys.path.insert(0,'$REPO/lib');from lets import install;assert not any('learning' in d for d in install.lets_dirs())\""
cd "$NOTES"; allowed "git add learning/closures.md"; cd "$REPO"
eval "$PICK lets" >/dev/null 2>&1
check "back to LETS's folder" "grep -A1 'Learning notes' \$XDG_CONFIG_HOME/lets/profile.md | grep -q \"Answer: LETS's folder\" && ! grep -q '\"notes\"' \$XDG_CONFIG_HOME/lets/config.json"
check "the learn skill writes front matter saying LETS made the note, and never says Obsidian" "grep -q 'made-by: LETS /lets:learn' '$REPO/plugin/skills/learn/SKILL.md' && ! grep -qi obsidian '$REPO/plugin/skills/learn/SKILL.md'"
check "build takes a task by its name as well as its number" "grep -q 'its name (its heading in kebab-case' '$REPO/plugin/skills/build/SKILL.md' && grep -q '\[task\]' '$REPO/plugin/skills/build/SKILL.md'"
check "change-revise takes a review comment after the change's name" "grep -q \"Anything I gave after the change's name is a review comment\" '$REPO/plugin/skills/change-revise/SKILL.md' && grep -q '<change-name> \[comment\]' '$REPO/plugin/skills/change-revise/SKILL.md'"
check "change-start takes the work in your own words, and asks when given nothing" "grep -q 'Otherwise the whole argument says what it' '$REPO/plugin/skills/change-start/SKILL.md' && grep -q 'With no argument, ask what I want to' '$REPO/plugin/skills/change-start/SKILL.md'"
check "both tools may write your additions, so /lets:add can save them" "grep -q '$XDG_CONFIG_HOME/lets/additions' \$HOME/.claude/settings.json && grep -q '$XDG_CONFIG_HOME/lets/additions' \$CODEX_HOME/config.toml"
check "/lets:help answers about LETS from its docs and changes nothing; /lets:next is the board" "grep -q 'Change nothing' '$REPO/plugin/skills/help/SKILL.md' && grep -q '~/lets/docs/' '$REPO/plugin/skills/help/SKILL.md' && grep -q 'the board' '$REPO/plugin/skills/next/SKILL.md'"
check "/lets:add shows the exact lines and saves only once you agree" "grep -q 'Show the exact lines' '$REPO/plugin/skills/add/SKILL.md' && grep -q 'Save.* only once I agree' '$REPO/plugin/skills/add/SKILL.md'"

echo "guard: bypasses and settings"
W="$T/plain"; mkdir -p "$W"; cd "$W"; git init -q; echo x > a.txt; git add a.txt; git commit -qm init
git config lets.kind own; git config lets.agents ship  # the commit and ship gates apply where agents may commit and ship
git checkout -q -b work  # agents commit to feature branches only
for c in "git commit --no-verify -m x" "git commit --no-veri -m x" "git commit -nm x" "git -c core.hooksPath=/dev/null commit -m x" \
         "GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null GIT_CONFIG_COUNT=1 git commit -m x" \
         "git config lets.walkthrough off" "git config lets.kind own" "git config lets.agents ship" \
         "python3 ~/lets/lib/lets/__main__.py walkthrough complete" "~/lets/bin/lets walkthrough 'pass'" \
         "bash -lc '~/lets/bin/lets walkthrough pass'" "touch .git/lets/walkthrough/passed.json" \
         "python3 -c 'import walkthrough; walkthrough.record_pass(\".\")'" "sed -i s/x/y/ .git/config" \
         "echo .scratch/ >> .git/info/exclude" "FLOOR_GUARD_ALLOW=x git commit -m y" "HUSKY=0 git commit -m y" \
         "bash -lc 'git commit --no-verify -m x'" "~/lets/bin/lets walkthrough complete" "lets walkthrough 'complete'" \
         "lets update" "lets profile length" "~/lets/bin/lets doctor --yes" "git config branch.work.lets-walked abc"; do blocked "$c"; done
for c in "~/lets/bin/lets setup --no-walkthrough-gate" "~/lets/bin/lets setup --own" "lets setup --agents ship" "~/lets/bin/lets uninstall" \
         "~/lets/bin/lets install --force" "echo '[lets] walkthrough = off' >> ~/.gitconfig" "git config --global lets.walkthrough off"; do blocked "$c"; done
blocked "$HOME/.gitconfig" Write
for c in "~/lets/bin/lets doctor" "~/lets/bin/lets walkthrough status" "~/lets/bin/lets note" "lets check" "~/lets/bin/lets where" \
         "~/lets/bin/lets sync" "~/lets/bin/lets note change add-x --mode agent" "lets profile" "~/lets/bin/lets statusline" \
         "git commit -am 'Explain why we never use --no-verify'" "gh pr view 3 --comments" "git config --get core.hooksPath" \
         "grep -rn record_pass lib/" "python3 -m json.tool .git/lets/walkthrough/passed.json" "head -40 ~/lets/bin/lets" \
         "git diff --stat -- bin/lets lib/lets.py" "gh api repos/o/r/pulls/12/merge" \
         "bash -lc \"git commit -m \\\"Don't call git commit --no-verify in the release script\\\"\""; do allowed "$c"; done
for c in "git config core.hooksPath .githooks" "timeout 120 git push origin main" "nice -n 5 git push origin main" \
         "env -u GIT_TRACE git push origin main" "sudo -u me git push origin main" "echo main | xargs git push origin" \
         "python3 -c 'open(\".git/lets/walkthrough/passed.json\", \"w\")'" "gh api -X PUT repos/o/r/pulls/12/merge"; do blocked "$c"; done
blocked ".git/hooks/pre-commit" Write
blocked "*** Begin Patch
*** Update File: .git/config" apply_patch
allowed "*** Begin Patch
*** Update File: README.md
+Never edit .git/hooks by hand." apply_patch
for c in "git config --get lets.check" "git add config/eng.yaml" "grep -rn 'walkthrough pass' README.md" "ls .git/lets" \
         "cat .git/lets/walkthrough/passed.json" "git commit -m 'Support -interactive flag'" "git status" \
         "git --no-pager log --oneline" "~/lets/bin/lets walkthrough scope"; do allowed "$c"; done
allowed "src/app.ts" Edit

echo "guard: ordinary work is never blocked"
git checkout -q -b daily
while IFS= read -r c; do [ -n "$c" ] && allowed "$c"; done < <(grep -v '^#' "$REPO/tests/ordinary_commands.txt")
git checkout -q work

echo "guard: work that can't be undone"
for c in "git reset --hard" "git reset --hard HEAD~1" "git checkout ." "git checkout -- ." "git checkout main -- ." \
         "git restore ." "git restore --staged --worktree ." "git clean -fd" "git clean -fdx" "git stash drop" "git stash clear" \
         "git branch -D old" "git switch -f main" "git checkout --force main"; do blocked "$c"; done
for c in "git checkout -b feature" "git checkout main" "git checkout -" "git checkout --track origin/x" "git switch -c y" \
         "git checkout -- src/a.ts" "git checkout main -- package-lock.json" "git restore src/a.ts" "git restore --staged ." \
         "git clean -fdx node_modules" "git clean -n" "git stash" "git stash pop" "git branch -d merged" "git reset HEAD~1" \
         "git commit -m 'Revert: git reset --hard was wrong'"; do allowed "$c"; done

echo "guard: what an agent commits"
stage src/a.test.ts 'it.skip("x", () => {})';            blocked "git commit -m skip"
python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":"git commit -m skip"},"cwd":sys.argv[1]}))' "$PWD" \
  | python3 "$REPO/agent-hooks/guard.py" 2>"$T/why.txt" >/dev/null
sed -n "s/^  ! //p" "$T/why.txt" > "$T/approve.sh"
check "a block prints the exact command that approves the finding" "grep -q '^git config --add branch.work.letsAllow ' '$T/approve.sh'"
sh "$T/approve.sh"
allowed "git commit -m skip-approved-by-you"
check "an approval covers only that finding" "printf 'it.skip(\"y\", () => {})\\n' >> src/a.test.ts && git add src/a.test.ts && [ \$(agent 'git commit -m another-skip') = 2 ]"
check "approvals belong to the branch: another branch doesn't inherit them" "git stash -q && git checkout -q -b other-branch && git stash pop -q && git add -A src && [ \$(agent 'git commit -m skip') = 2 ]"
git checkout -q -; git config --remove-section branch.work 2>/dev/null; git branch -q -D other-branch; reset
for c in "git config --add branch.feat.letsAllow 'anything'" "git config --add 'branch.feat/x.letsallow' anything" \
         "git config --add lets.allow x" "git config LETS.check true" "git config --remove-section lets" \
         "git config unset lets.check" "git config --rename-section lets old"; do blocked "$c"; done
for c in "git config get lets.base" "git config --get-all branch.feat.letsallow" "git config --remove-section branch.old" \
         "git config user.name 'A Person'"; do allowed "$c"; done
stage src/b.test.ts 'test.concurrent.only("x", () => {})'; blocked "git commit -m only"; reset
stage src/b.test.ts 'test.concurrent.only("x", () => {})'; blocked "git --no-pager commit -m only"; reset
stage src/fit.py 'model.fit(x, y)';                        allowed "git commit -m fit"; reset
stage src/est.py 'def fit(self, X, y): return self';       allowed "git commit -m estimator"; reset
stage src/c.ts '// eslint-disable-next-line no-console -- debug output'; allowed "git commit -m reasoned"; reset
stage src/d.ts '/* eslint-disable */';                     blocked "git commit -m bare"; reset
stage src/e.py 'import stripe  # type: ignore[import-untyped]'; allowed "git commit -m coded"; reset
stage src/f.py 'import stripe  # type: ignore';             blocked "git commit -m bare-ignore"; reset
stage src/g.py 'raise NotImplementedError';                allowed "git commit -m abstract"; reset
stage CODING_STANDARDS.md 'Never add @ts-ignore.';         allowed "git commit -m standards"; reset
printf '{"jest":{"coverageThreshold":{"global":{"lines":90}}}}\n' > package.json; git add package.json; git commit -qm cov
printf '{"jest":{"coverageThreshold":{"global":{"lines":80}}}}\n' > package.json; git add package.json
allowed "git commit -m lower-is-a-question-for-the-walkthrough"; reset
printf '[tool.pylint]\nmax-branches = 15\n' > pyproject.toml; git add pyproject.toml; git commit -qm pylint
printf '[tool.pylint]\nmax-branches = 12\n' > pyproject.toml; git add pyproject.toml
allowed "git commit -m stricter"; reset
stage src/a.ts 'export const a = 1'; git commit -qm a
echo 'it.only("x", () => {})' >> src/a.ts
blocked "git commit -am sneaky"
blocked "git commit -m pathspec src/a.ts"
blocked "git commit -o -m only src/a.ts"
mkdir -p sub; blocked "cd sub && git commit -am from-a-subfolder"
blocked "cd \"\$(git rev-parse --show-toplevel)\" && git commit -am from-the-top"
blocked "cd \"\$(mktemp -d)\" && git commit -am somewhere-unknown"
blocked "cd /nonexistent && git commit -am nowhere"
allowed "git commit -m staged-only-and-clean"; reset
git config lets.check "false"; stage src/h.ts 'export const h = 1'; blocked "git commit -m check-fails"
git config lets.check "true"; allowed "git commit -m check-passes"; reset; git config --unset lets.check
git checkout -q -b other; stage src/n.py 'x = 1  # noqa'; git commit -qm noqa
git checkout -q work; stage src/m.ts 'export const m = 1'; git commit -qm m
git merge -q --no-commit --no-ff other 2>/dev/null
allowed "git commit -m merge"
stage src/merge.test.ts 'it.skip("hacked while resolving", () => {})'
blocked "git commit --no-edit"
blocked "git merge --continue"
git merge --abort 2>/dev/null; reset
mkdir -p tests; printf 'def test_one():\n    assert 1\n\ndef test_two():\n    assert 2\n' > tests/test_x.py; git add tests; git commit -qm tests
git checkout -q -b tests-gone; git config lets.base work; printf 'def test_one():\n    assert 1\n' > tests/test_x.py; git add tests
allowed "git commit -m drop-a-test"; git commit -qm drop-a-test
check "the walkthrough asks about a dropped test, by name" "\"$LETS\" walkthrough scope | grep -q '^ask: (tests): 1 fewer test.*test_two'"
git config lets.walkthrough off; blocked "gh pr create --fill"; git config --unset lets.walkthrough
blocked "gh pr create --fill"
"$LETS" walkthrough complete > "$T/pass.txt" 2>&1
check "completing the walkthrough names the loosening it accepts" "grep -q 'test_two' '$T/pass.txt'"
allowed "gh pr create --fill"
stage tests/test_y.py 'import pytest
pytest.importorskip("clickhouse_connect")'; allowed "git commit -m new-integration-test-skips-without-its-service"; reset
stage tests/test_z.py '@pytest.mark.skip(reason="fails")'; blocked "git commit -m new-test-skipped-outright"; reset
git config --unset lets.base; git checkout -q work
mkdir -p src; printf 'it.only("staged in the same call", () => {})\n' > src/z.test.ts
blocked "git add src/z.test.ts && git commit -m add-and-commit"
blocked "git add -A; git commit -m add-all-and-commit"
echo notes > notes.txt; allowed "git add notes.txt && git commit -m only-the-notes"; rm -f notes.txt
rm -f src/z.test.ts

echo "guard: shipping"
git checkout -q main; git init -q --bare "$T/remote.git"; git remote add origin "$T/remote.git"; git push -q origin main
git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
for c in "git push" "git push origin HEAD" "git push -u origin HEAD" "git push origin @" "git push origin main" \
         "git push origin main # don't" "git push --force origin HEAD" "git push origin +HEAD:main" "git push origin HEAD:refs/heads/main" \
         "git push origin --delete main" "git push origin :main" "git push --all origin" "gh pr merge 12 --squash" \
         "gh -R team/repo pr merge 12" "gh pr merge 99 --admin" "gh api -X PUT repos/o/r/pulls/12/merge" "glab mr merge 12 --yes" \
         "git push origin HEAD:develop"; do blocked "$c"; done
for c in "cd \"\$(git rev-parse --show-toplevel)\" && git push origin HEAD" "(git push origin main)" "{ git push origin main; }" \
         "if true; then git push origin main; fi" "git push --repo=origin main" "git push origin 'refs/heads/*:refs/heads/*'" \
         "gh pr review 3 --approve" "glab mr approve 2" "glab mr accept 2" "git push -o merge_request.merge_when_pipeline_succeeds origin HEAD"; do blocked "$c"; done
git checkout -q -b feat; stage src/feature.ts 'export const feature = 1'; git commit -qm feat
for c in "git push origin feat" "git push -u origin HEAD" "git push --force-with-lease origin feat" "git push"; do allowed "$c"; done
for c in "gh pr new --fill" "glab mr new --fill" "glab mr update 2 -r" "git push -o merge_request.create origin feat" \
         "gh pr review 3 --approve" "glab mr approve 2" "git push -o merge_request.create -o merge_request.merge_when_pipeline_succeeds origin feat"; do blocked "$c"; done
allowed "gh pr review 3 --comment"
blocked "gh pr create --fill"
check "scope lists the branch's file" "\"$LETS\" walkthrough scope | grep -qx src/feature.ts"
echo 'export const feature = 1.5' > src/feature.ts
check "scope says what is uncommitted" "\"$LETS\" walkthrough scope 2>&1 >/dev/null | grep -q 'uncommitted'"
"$LETS" walkthrough complete >/dev/null
allowed "gh pr create --fill"
git commit -qam "feature 1.5"
check "a walkthrough covers committed content only: the new commit needs its own" "\"$LETS\" walkthrough scope | grep -qx src/feature.ts"
blocked "gh pr create --fill"
git reset -q --hard HEAD~1
allowed "gh pr create --fill"
allowed "glab mr create --fill"
allowed "git push -o merge_request.create -o merge_request.target=main origin feat"
git checkout -q -b feat-renamed; allowed "gh pr create --fill"
blocked "gh pr create --title 'Add export' --body '🤖 Generated with Claude Code'"; allowed "gh pr create --title 'Add export' --body 'Adds the CSV export.'"
git checkout -q -b stacked; stage src/stacked.ts 'export const s = 1'; git commit -qm stacked
check "a stacked branch only needs a walkthrough of its own files" "[ \"\$(\"$LETS\" walkthrough scope | tail -n +2)\" = src/stacked.ts ]"
git checkout -q feat
git checkout -q main; stage team.txt 'teammate'; git commit -qm team; git push -q origin main; git checkout -q feat
git merge -q main -m "merge main" 2>/dev/null
check "teammates' files merged in from main never enter the scope" "! \"$LETS\" walkthrough scope | grep -q team.txt"
allowed "gh pr ready"
echo 'export const feature = 2' > src/feature.ts; git commit -qam change
blocked "gh pr ready"
check "only the changed file needs a new walkthrough" "[ \"\$(\"$LETS\" walkthrough scope | tail -n +2)\" = src/feature.ts ]"
git config lets.walkthrough off; allowed "gh pr create --fill"; git config --unset lets.walkthrough
"$LETS" walkthrough complete >/dev/null
stage src/sub.test.ts 'it.only("from a subagent", () => {})'; git commit -qm "commit the hook never saw"
"$LETS" walkthrough complete >/dev/null
blocked "gh pr create --fill"
check "the ship gate names the weakened gate" "python3 -c 'import json,sys; print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"gh pr create\"},\"cwd\":sys.argv[1]}))' \"\$PWD\" | python3 \"$REPO/agent-hooks/guard.py\" 2>&1 | grep -q 'sub.test.ts'"
git reset -q --hard HEAD~1
TM="$T/teammate"; git clone -q "$T/remote.git" "$TM"; (cd "$TM" && mkdir -p tests && printf 'import pytest\n@pytest.mark.skip(reason="flaky")\ndef test_t():\n    assert 1\n' > tests/test_team.py && git add tests && git commit -qm team-skip && git push -q origin main)
git fetch -q origin; git merge -q origin/main -m "merge origin/main" 2>/dev/null; "$LETS" walkthrough complete >/dev/null
allowed "gh pr create --base main --fill"
allowed "glab mr create --target-branch main --fill"
D="$T/dev"; mkdir -p "$D"; cd "$D"; git init -q -b develop; stage a.txt x; git commit -qm init; git checkout -q -b f; stage b.txt y; git commit -qm b
check "a repo whose default branch is develop scopes only the branch's files" "[ \"\$(\"$LETS\" walkthrough scope | tail -n +2)\" = b.txt ]"
GF="$T/gitflow"; mkdir -p "$GF"; cd "$GF"; git init -q -b main; stage m.txt m; git commit -qm m; git checkout -q -b develop
stage d1.txt d; git commit -qm d1; stage d2.txt d; git commit -qm d2; git checkout -q -b feature/x; stage x.txt x; git commit -qm x
check "a gitflow repo without origin/HEAD scopes against develop, not main" "[ \"\$(\"$LETS\" walkthrough scope | tail -n +2)\" = x.txt ]"
SC="\"$LETS\" walkthrough scope | tail -n +2 | sort | tr '\\n' ' '"
check "a repo's own base (lets setup --base) decides the scope" "git config lets.base main && [ \"\$($SC)\" = 'd1.txt d2.txt x.txt ' ]"
check "a branch's own base wins (lets note base, for stacked pull requests)" "\"$LETS\" note base develop >/dev/null && [ \"\$($SC)\" = 'x.txt ' ]"
check "the base says where it came from" "python3 -c \"import sys;sys.path.insert(0,'$REPO/lib');from lets.walkthrough import base_branch;print(base_branch('.'))\" | grep -q \"'develop', 'set for this branch'\""
check "lets note base auto goes back to the repo's base" "\"$LETS\" note base auto >/dev/null && [ \"\$($SC)\" = 'd1.txt d2.txt x.txt ' ]"
git config --unset lets.base

echo "guard: git stays local by default"
L="$T/local"; mkdir -p "$L"; cd "$L"; git init -q; echo x > a.txt; git add a.txt; git commit -qm init; git config lets.kind own
for c in "git commit -m x" "git commit -am x" "git add -A && git commit -m x" "git merge feature" "git rebase main" \
         "git cherry-pick abc123" "git revert HEAD" "git pull" "git am < p.patch" "git push -u origin feat" "git push" \
         "gh pr create --fill" "glab mr create --fill" "bash -lc 'git commit -m x'"; do blocked "$c"; done
for c in "git checkout -b feat/cart-checkout" "git switch -c fix/parser" "git branch wip" "git stash" "git stash pop" \
         "git checkout main" "git merge --abort" "git rebase --abort" "git pull --ff-only" "git fetch origin" \
         "git status" "git diff" "git log --oneline -5" "git add src/a.ts" "gh issue list" "gh pr view 3"; do allowed "$c"; done
git config lets.agents commit
blocked "git commit -m on-main"; git checkout -q -b feat/x
allowed "git commit -m x"; blocked "git push -u origin HEAD"; blocked "gh pr create --fill"; git checkout -q main
git config --unset lets.agents
check "the block tells the agent the commit is mine" "python3 -c 'import json,sys; print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git commit -m x\"},\"cwd\":sys.argv[1]}))' \"\$PWD\" | python3 \"$REPO/agent-hooks/guard.py\" 2>&1 | grep -q 'I commit myself'"

echo "guard: a repo that isn't mine"
N="$T/notmine"; mkdir -p "$N"; cd "$N"; git init -q; echo x > a.txt; git add a.txt; git commit -qm init
for c in "gh issue list" "gh pr view 3" "gh api repos/o/r/issues" "glab mr list" "glab issue note 7 -m hi" \
         "git checkout -b claude/fix-parser" "git switch -c fix/codex-cleanup" "git branch copilot-wip" \
         "git worktree add -b claude/x ../x" "git branch -m feat/claude-tweaks"; do blocked "$c"; done
check "a repo nobody has set up is treated as not mine" "[ \$(agent 'gh issue list') = 2 ]"
git config lets.kind other
for c in "git checkout -b fix/cart-parser" "git switch -c feat/ai-model-loader" "git branch -m fix/agent-based-sim"; do allowed "$c"; done
git config lets.agents commit; git checkout -q -b fix/parser
blocked "git commit -m 'Fix parser

Co-Authored-By: Claude <noreply@anthropic.com>'"
blocked "git commit -m 'Fix parser (generated with Claude Code)'"
allowed "git commit -m 'Fix the cart parser for empty lines'"
allowed "git commit -m 'Fix the parser' -- /tmp/claude-notes/x.txt"
allowed "git commit -F /home/me/claude-work/msg.txt"
blocked "git commit -F msg.txt --trailer 'Co-Authored-By: Claude <noreply@anthropic.com>'"
blocked "git commit -F - <<'EOF'
Fix parser

Co-Authored-By: Claude <noreply@anthropic.com>
EOF"
OWNP="$T/own-planning"; mkdir -p "$OWNP"; git -C "$OWNP" init -q; git -C "$OWNP" config lets.kind own; git -C "$OWNP" config lets.role planning; git -C "$OWNP" config lets.agents commit
blocked "cd $OWNP && git add -A && git commit -m 'epic-start: x (drafted with Claude)'"
allowed "cd $OWNP && git add -A && git commit -m 'epic-start: x'"
git config lets.kind own
blocked "git commit -m 'Fix parser

Co-Authored-By: Claude <noreply@anthropic.com>'"
blocked "git checkout -b claude/fix-parser"
blocked "gh pr create --title 'Fix parser' --body 'Generated with Claude Code'"
git config lets.ai-credit 'trailer:Assisted-by: Claude Code'
check "lets where shows this repo's AI credit" "\"$LETS\" where | grep -q 'AI credit: *end each commit message with .Assisted-by: Claude Code. (set for this repo)'"
blocked "git commit -m 'Fix parser'"
allowed "git commit -m 'Fix parser' -m 'Assisted-by: Claude Code'"
allowed "git commit -F - <<'EOF'
Fix parser

Assisted-by: Claude Code
EOF"
blocked "git commit -m 'Fix parser (written by Claude)' -m 'Assisted-by: Claude Code'"
blocked "git commit -m 'Fix parser' -m 'Co-Authored-By: Claude <noreply@anthropic.com>'"
blocked "git checkout -b claude/fix-parser"
blocked "gh pr create --title 'Fix parser' --body 'Generated with Claude Code'"
PRTEXT="python3 -c \"import sys,os;sys.path.insert(0,'$REPO/lib');from lets import guard;guard.check_commit_message(sys.argv[1],os.getcwd())\""
check "the pull request text check lets a plain description through (opening it is gated separately)" "eval \"\$PRTEXT \\\"gh pr create --title 'Fix parser' --body 'Fixes the parser.'\\\"\""
git config lets.ai-credit 'trailer-pr:Co-authored-by: Claude <noreply@anthropic.com>'
allowed "git commit -m 'Fix parser' -m 'Co-authored-by: Claude <noreply@anthropic.com>'"
blocked "gh pr create --title 'Fix parser' --body 'Fixes the parser.'"
printf '%s\n' "gh pr create --title 'Fix parser' --body 'Fixes the parser." "" "Made with AI assistance.'" > "$T/pr.txt"
check "with trailer-pr, a description ending in the note gets through the text check" "python3 -c \"import sys,os;sys.path.insert(0,'$REPO/lib');from lets import guard;guard.check_commit_message(open('$T/pr.txt').read(),os.getcwd())\""
blocked "gh pr create --title 'Fix parser' --body 'Fixes the parser with Claude.

Made with AI assistance.'"
git config --unset lets.ai-credit
check "lets where shows no AI credit by default, from your profile" "\"$LETS\" where | grep -q 'AI credit: *none: no AI mention in commits or pull requests (your profile)'"
git config lets.kind other
blocked "cd $OWNP && git commit -m x && cd $N && git commit -m 'Fix (generated with Claude Code)'"
git config --unset lets.agents

echo "guard: edits are checked as they're made"
E="$T/edits"; mkdir -p "$E/src"; cd "$E"; git init -q
printf 'import { it, expect } from "vitest";\nit("adds", () => {\n  expect(1 + 1).toBe(2);\n});\n' > src/a.test.ts
printf 'def f(x):\n    return x\n' > src/m.py; git add -A; git commit -qm init
edit() { python3 -c 'import json,sys; print(json.dumps({"tool_name":sys.argv[1],"tool_input":json.loads(sys.argv[2]),"cwd":sys.argv[3]}))' "$1" "$2" "$PWD" | python3 "$REPO/agent-hooks/guard.py" >/dev/null 2>&1; echo $?; }
ed_blocked() { local r; r=$(edit "$2" "$3"); if [ "$r" = 2 ]; then ok "blocks edit: $1"; else bad "blocks edit: $1 (exit $r)"; fi; }
ed_allowed() { local r; r=$(edit "$2" "$3"); if [ "$r" = 0 ]; then ok "allows edit: $1"; else bad "allows edit: $1 (exit $r)"; fi; }
ed_blocked "Edit makes a test skip" Edit '{"file_path":"src/a.test.ts","old_string":"it(\"adds\"","new_string":"it.skip(\"adds\""}'
ed_allowed "Edit changes a test's body" Edit '{"file_path":"src/a.test.ts","old_string":"1 + 1","new_string":"2 + 0"}'
ed_blocked "Write a new focused test" Write '{"file_path":"src/b.test.ts","content":"it.only(\"x\", () => {});\n"}'
ed_allowed "Write a new test" Write '{"file_path":"src/b.test.ts","content":"it(\"x\", () => {});\n"}'
ed_blocked "MultiEdit adds a bare noqa" MultiEdit '{"file_path":"src/m.py","edits":[{"old_string":"return x","new_string":"return x  # noqa"}]}'
ed_allowed "MultiEdit adds a named noqa" MultiEdit '{"file_path":"src/m.py","edits":[{"old_string":"return x","new_string":"return x  # noqa: E501"}]}'
ed_blocked "Codex apply_patch adds a bare type: ignore" apply_patch '{"command":"*** Begin Patch\n*** Update File: src/m.py\n@@\n def f(x):\n-    return x\n+    return x  # type: ignore\n*** End Patch"}'
ed_blocked "Codex apply_patch adds a focused test file" apply_patch '{"command":"*** Begin Patch\n*** Add File: src/c.test.ts\n+describe.only(\"c\", () => {});\n*** End Patch"}'
ed_allowed "Codex apply_patch, an ordinary change" apply_patch '{"command":"*** Begin Patch\n*** Update File: src/m.py\n@@\n def f(x):\n-    return x\n+    return x + 1\n*** End Patch"}'
perl -pi -e 's/it\("adds"/it.skip("adds"/' src/a.test.ts  # perl: sed -i differs on macOS
ed_allowed "a skip I made myself isn't charged to the agent's next edit" Edit '{"file_path":"src/a.test.ts","old_string":"1 + 1","new_string":"2 + 0"}'
git checkout -q -- .
python3 -c 'import json,sys; print(json.dumps({"tool_name":"Edit","tool_input":{"file_path":"src/a.test.ts","old_string":"it(\"adds\"","new_string":"it.skip(\"adds\""},"cwd":sys.argv[1]}))' "$PWD" | python3 "$REPO/agent-hooks/guard.py" 2>&1 >/dev/null | sed -n "s/^  ! //p" > "$T/approve-edit.sh"
sh "$T/approve-edit.sh"
ed_allowed "an edit you approved for the branch" Edit '{"file_path":"src/a.test.ts","old_string":"it(\"adds\"","new_string":"it.skip(\"adds\""}'


echo "repo setup: plans in the repo"
O="$T/owned"; mkdir -p "$O"; cd "$O"; git init -q; echo x > README.md; git add .; git commit -qm init
AS="$T/has-agent-setup"; mkdir -p "$AS/.claude/skills/tdd"; (cd "$AS" && git init -q && echo x > .claude/skills/tdd/SKILL.md && git add -A && git commit -qm skills)
(cd "$AS" && "$LETS" setup --planning in-repo --yes </dev/null >"$T/as.log" 2>&1); rc=$?
check "plans won't go into a repo that has another agent setup (it says why, and changes nothing)" "[ $rc -ne 0 ] && grep -q 'already has agent setup' '$T/as.log' && [ -z \"\$(git -C '$AS' config lets.kind)\" ] && [ ! -e '$AS/plans' ]"
(cd "$AS" && "$LETS" setup --planning private --url "$T/as-plans.git" </dev/null >"$T/as.log" 2>&1); rc=$?
check "with a separate planning repo, it warns about the other setup and stops unless I agree" "[ $rc -ne 0 ] && grep -q 'Agent setup found' '$T/as.log' && grep -q 'Nothing was changed' '$T/as.log'"
FP="$T/foreign-plans"; mkdir -p "$FP/plans"; (cd "$FP" && git init -q && echo mine > plans/q3.md && git add -A && git commit -qm plans)
(cd "$FP" && "$LETS" setup --planning in-repo --yes </dev/null >"$T/fp.log" 2>&1); rc=$?
check "a plans/ folder that isn't LETS's is never used (it says why)" "[ $rc -ne 0 ] && grep -q \"plans/ folder that isn't LETS's\" '$T/fp.log' && [ ! -e '$FP/plans/openspec' ]"
"$LETS" setup --planning in-repo --check "true" --yes </dev/null >"$T/own.log" 2>&1; check "setup with plans in this repo exits 0" "[ $? -eq 0 ]"
check "the plans live in plans/, with OpenSpec, LETS's rules and a README for teammates, and none of OpenSpec's agent files" "[ -f plans/openspec/config.yaml ] && grep -q 'Each numbered group is one task' plans/openspec/config.yaml && grep -q 'kept by \\[LETS\\]' plans/README.md && [ ! -e openspec ] && [ ! -e .claude/skills/openspec-propose ]"
check "build choices come from the profile, recorded per repo" "[ \"\$(git config lets.build)\" = pair ] && [ \"\$(git config lets.tests)\" = propose ] && \"$LETS\" where | grep -q 'build:  *pair · test-first: propose · git: local'"
check "lets where prints plans/ as the planning root, and the quick check" "\"$LETS\" where | grep -q \"planning root: $O/plans\" && \"$LETS\" where | grep -q 'home:  *plans in this repo' && \"$LETS\" where | grep -q 'check:  *true'"
"$LETS" setup --planning in-repo --build agent --tests always --check "true" --yes </dev/null >/dev/null 2>&1
check "a repo can choose differently from the profile" "[ \"\$(git config lets.build)\" = agent ] && [ \"\$(git config lets.tests)\" = always ]"
"$LETS" setup --planning in-repo --build pair --tests propose --check "true" --yes </dev/null >/dev/null 2>&1
mkdir -p .lets/handoffs; echo t > .lets/handoffs/2026-01-01-0900-x.md
check "handoffs are never committed (setup ignores .lets/ in this repo only)" "! git status --porcelain --untracked-files=all | grep -q .lets && grep -qx '.lets/' .git/info/exclude"
check "no git hooks are installed" "[ ! -e .git/hooks/pre-commit ] && [ ! -e .git/hooks/pre-push ] && [ ! -e .git/hooks/commit-msg ]"
check "no CI files are added" "[ ! -e .github ] && [ ! -e tools ]"
mkdir -p "$XDG_CONFIG_HOME/lets/additions" plans/additions; echo "Also run make lint." > "$XDG_CONFIG_HOME/lets/additions/build.md"; echo "Link the Jira ticket." > plans/additions/walkthrough.md
check "lets where lists the additions: yours, then the team's" "\"$LETS\" where | grep -q 'additions: .*additions/build.md, .*plans/additions/walkthrough.md'"
rm -rf plans/additions
git add -A; git commit -qm setup
mkdir -p src; printf 'it.skip("later", () => {})\n' > src/w.test.ts; git add src
check "my own commit of a skip goes through (no hooks; the guard binds agents only)" "git commit -qm skip"
check "lets check lists weakened gates in the branch, committed or not" "printf 'x = 1  # noqa\n' > src/n.py && \"$LETS\" check | grep -q 'bare noqa'"
rm -f src/n.py
check "lets check --run runs the quick check" "\"$LETS\" check --run | grep -q 'Running true'"
"$LETS" setup --remove >/dev/null 2>&1
check "setup --remove clears the settings and leaves the plans" "[ -z \"\$(git config lets.build)\" ] && [ -d plans/openspec ]"
"$LETS" setup --planning in-repo --check "true" --yes </dev/null >/dev/null 2>&1

echo "repo setup: a private planning repo"
G="$T/team-app"; mkdir -p "$G"; cd "$G"; git init -q; echo "# Team" > CLAUDE.md; echo "# Terms" > GLOSSARY.md; git add .; git commit -qm init
"$LETS" setup --yes </dev/null >"$T/guest.log" 2>&1
check "setup without a terminal assumes private plans, and stops without a planning repo URL" "[ \"\$(git config lets.kind)\" != own ] && grep -q 'planning repo needs its clone URL' '$T/guest.log' && [ ! -e \$HOME/plans ]"
"$LETS" setup --planning private --url "$T/team-app-plans.git" </dev/null >"$T/guest.log" 2>&1
check "without a terminal or --yes, setup changes nothing" "grep -q 'Nothing was changed' '$T/guest.log' && [ -z \"\$(git config lets.kind)\" ]"
git init -q --bare "$T/team-app-plans.git"
"$LETS" setup --planning private --url "$T/team-app-plans.git" --yes </dev/null >"$T/guest.log" 2>&1; check "setup with a private planning repo exits 0" "[ $? -eq 0 ]"
PL="$HOME/plans/team-app-plans"
check "the planning repo is cloned to ~/plans/<its own name>, recorded ~-relative so settings can travel" "[ -d '$PL/.git' ] && [ \"\$(git config lets.plans)\" = '~/plans/team-app-plans' ] && [ \"\$(git config lets.kind)\" = other ] && grep -q '\"~/plans\"' \$XDG_CONFIG_HOME/lets/config.json"
check "setup lets both tools write planning repos where it put them" "grep -q '$HOME/plans' \$HOME/.claude/settings.json && grep -q '$HOME/plans' \$CODEX_HOME/config.toml"
check "lets where prints the planning root and the code repo" "\"$LETS\" where | grep -q \"planning root: $PL\" && \"$LETS\" where | grep -q \"code repo:     $G\""
check "the planning repo has the layout, LETS's settings and a first commit" "[ -f '$PL/openspec/config.yaml' ] && [ -f '$PL/README.md' ] && [ \"\$(git -C '$PL' config lets.role)\" = planning ] && [ \"\$(git -C '$PL' config lets.agents)\" = commit ] && git -C '$PL' log --oneline | grep -q 'lets setup: plans for team-app' && grep -q '\"team-app\"' '$PL/repos.json'"
check "the code repo stays clean: nothing agent-related in it" "[ -z \"\$(git status --porcelain --untracked-files=all)\" ] && [ ! -e plans ] && [ ! -e .lets ]"
check "setup adds no per-repo Claude Code settings (install's global settings already keep AI attribution out)" "[ ! -e .claude/settings.local.json ]"
check "the repo records which LETS set it up, and lets where says the team hasn't agreed" "[ \"\$(git config lets.version)\" = 1.1.0 ] && \"$LETS\" where | grep -q \"team:  *hasn't agreed\""
check "without the team's agreement, plans can't go in the repo and agents can't ship" "! \"$LETS\" setup --team-agreed no --planning in-repo --yes </dev/null >/dev/null 2>&1 && ! \"$LETS\" setup --team-agreed no --planning private --agents ship --yes </dev/null >/dev/null 2>&1"
# an upgrade from 1.0.x: no lets.version, and the per-repo attribution file 1.0.x wrote (plus a permission of mine)
git config --unset lets.version; mkdir -p .claude
printf '{"attribution":{"commit":"","pr":""},"includeCoAuthoredBy":false,"permissions":{"allow":["WebSearch"]}}\n' > .claude/settings.local.json
check "doctor names a repo an older LETS set up, and what to run" "\"$LETS\" doctor | grep -q 'set up before LETS 1.1.0: .*team-app'"
check "lets where tells the agent to have it updated" "\"$LETS\" where | grep -q 'setup:  *by an earlier LETS'"
check "the session-start check says so too" "sh '$REPO/agent-hooks/session-start.sh' | grep -q 'set up by an earlier LETS'"
check "install's next steps list it" "\"$LETS\" install --yes 2>&1 | grep -q 'Set up before LETS 1.1.0: .*team-app'"
B="$(git config lets.build)/$(git config lets.tests)/$(git config lets.agents)/$(git config lets.plans)"
"$LETS" setup --team-agreed no --yes </dev/null >"$T/upgrade.log" 2>&1
check "setup in an older repo asks only what's new, and keeps every other answer" "grep -q 'was set up by an earlier LETS' '$T/upgrade.log' && grep -q 'now up to date with LETS 1.1.0' '$T/upgrade.log' && [ \"\$(git config lets.version)\" = 1.1.0 ] && [ \"\$(git config lets.kind)\" = other ] && [ \"$B\" = \"\$(git config lets.build)/\$(git config lets.tests)/\$(git config lets.agents)/\$(git config lets.plans)\" ]"
check "it takes out the old attribution settings and keeps my own" "python3 -c \"import json;d=json.load(open('.claude/settings.local.json'));assert 'attribution' not in d and 'includeCoAuthoredBy' not in d and d['permissions']=={'allow':['WebSearch']}\""
check "afterwards nothing is reported as older" "! \"$LETS\" doctor | grep -q 'set up before LETS' && ! \"$LETS\" where | grep -q 'setup: '"
rm -rf .claude
check "lets where in the planning repo says what it is" "(cd '$PL' && \"$LETS\" where | grep -q 'home:  *a planning repo')"
"$LETS" sync >"$T/sync.log" 2>&1
check "lets sync without an upstream says so" "grep -q 'no upstream' '$T/sync.log'"
(cd "$PL" && mkdir -p epics/x && echo '# map' > epics/x/map.md)
(cd "$PL" && allowed "git add -A && git commit -m 'epic-start: x'")
(cd "$PL" && blocked "git push origin main")
mkdir -p docs/adr; echo "# Use Kafka" > docs/adr/0002-kafka.md
check "an ADR I write for the team still shows in git status" "git status --porcelain --untracked-files=all | grep -q docs/adr/0002-kafka.md"
check "the team's CLAUDE.md is untouched" "git diff --quiet -- CLAUDE.md"
git add docs; git commit -qm adr
git checkout -q -b gwork
git config lets.agents commit
echo "more" >> GLOSSARY.md; git add GLOSSARY.md; blocked "git commit -m glossary"; git checkout -q HEAD -- GLOSSARY.md
stage src/x.ts 'export const x = 1'; allowed "git commit -m code"; reset
mkdir -p packages/web; echo "# web" > packages/web/AGENTS.md; git add -f packages/web/AGENTS.md
blocked "git commit -m nested-agents-md"; git reset -q; rm -rf packages
mkdir -p plans/openspec/specs; echo x > plans/openspec/specs/x.md; blocked "git add -f plans && git commit -m planning-files"; git reset -q; rm -rf plans
blocked "gh issue list"
git config --unset lets.agents
git checkout -q -b gfeat; stage src/y.ts 'export const y = 1'; git commit -qm y; echo "a term" >> GLOSSARY.md
check "the team's docs, edited locally, don't hold up a walkthrough" "\"$LETS\" walkthrough complete"
git checkout -q -- GLOSSARY.md
GA="$T/agents-only"; mkdir -p "$GA"; cd "$GA"; git init -q; echo "# Team rules" > AGENTS.md; git add .; git commit -qm init
git init -q --bare "$T/plans-agents.git"
"$LETS" setup --planning private --url "$T/plans-agents.git" --plans-dir "$HOME/plans" --yes >/dev/null 2>&1
check "a repo that only has AGENTS.md keeps it loaded in Claude Code, privately" "grep -qx '@AGENTS.md' CLAUDE.local.md && [ -z \"\$(git status --porcelain --untracked-files=all)\" ]"

echo "repo setup: several repos sharing a team planning repo"
GR="$T/shop"; mkdir -p "$GR"; for r in api web; do mkdir -p "$GR/$r"; (cd "$GR/$r" && git init -q && echo $r > README.md && git add . && git commit -qm init); done
git init -q --bare "$T/shop-plans.git"
(cd "$GR" && "$LETS" setup --mode group --path "$GR" --repos api,web --planning team --url "$T/shop-plans.git" --plans-dir "$GR" --check '' --yes </dev/null >"$T/group.log" 2>&1); rc=$?
check "setup of a group exits 0, cloning the planning repo beside the repos" "[ $rc -eq 0 ] && [ -d '$GR/shop-plans/.git' ]"
check "both repos point at the shared planning repo, for the team" "[ \"\$(git -C '$GR/api' config lets.sharing)\" = team ] && [ \"\$(git -C '$GR/web' config lets.kind)\" = own ]"
check "lets where in a member names the group" "(cd '$GR/api' && \"$LETS\" where | grep -q 'group:  *api, web')"
check "lets where in the group folder names the repos" "(cd '$GR' && \"$LETS\" where | grep -q 'home:  *a group folder')"
mkdir -p "$GR/admin"; (cd "$GR/admin" && git init -q && echo a > README.md && git add . && git commit -qm init)
check "a new repo beside the group is offered the group's planning repo (no terminal: it joins)" "(cd '$GR/admin' && \"$LETS\" setup --mode one --check '' --yes </dev/null >/dev/null 2>&1) && (cd '$GR/admin' && \"$LETS\" where | grep -q 'group:  *admin, api, web')"
# a plain folder of clones, with a virtualenv and a folder of loose notes beside them (like NO-ARC)
NA="$T/no-arc"; mkdir -p "$NA/.venv/bin" "$NA/.codex"; echo "# plan" > "$NA/.codex/PLAN.md"
for r in core-tools api thinfsm; do mkdir -p "$NA/$r"; (cd "$NA/$r" && git init -q -b main && echo x > a && git add a && git commit -qm init); done
git init -q --bare "$T/no-arc-plans.git"
(cd "$NA" && "$LETS" setup --mode group --path "$NA" --repos core-tools,api --team-agreed yes --planning private --url "$T/no-arc-plans.git" --plans-dir "$T/plans-elsewhere" --check '' --yes </dev/null >"$T/na.log" 2>&1); rc=$?
check "a folder of clones with other folders beside them sets up as a group, with only the repos chosen" "[ $rc -eq 0 ] && (cd '$NA' && \"$LETS\" where | grep -q 'code repos:  *api, core-tools') && [ -z \"\$(git -C '$NA/thinfsm' config lets.kind)\" ] && [ -f '$NA/.codex/PLAN.md' ]"
check "private plans with the team's agreement: the code repos are marked as agreed" "[ \"\$(git -C '$NA/api' config lets.kind)\" = own ] && [ \"\$(git -C '$NA/api' config lets.sharing)\" = private ]"
# the base branch is asked whenever there's a choice, with the remote's default first
BB="$T/base-choice"; git init -q --bare "$BB.git"; git clone -q "$BB.git" "$BB" 2>/dev/null; cd "$BB"; echo x > a; git add a; git commit -qm init; git push -q origin HEAD:main 2>/dev/null; git checkout -q -b develop; git push -q origin develop 2>/dev/null; git remote set-head origin main >/dev/null; cd "$REPO"
check "setup asks for the base when develop sits beside the remote's default, and keeps the default unset" "python3 -c \"
import sys;sys.path.insert(0,'$REPO/lib');from lets import setup,ui;import pathlib
asked=[];ui.interactive=lambda:True
ui.select=lambda q,o,d=None,e=None:(asked.append([x[0] for x in o]),'develop')[1]
assert setup.ask_base(pathlib.Path('$BB'),None)=='develop' and asked==[['main','develop']]
ui.select=lambda q,o,d=None,e=None:'main'
assert setup.ask_base(pathlib.Path('$BB'),None) is None\""

echo "moving plans: a private planning repo into the repo"
MV="$T/move-app"; mkdir -p "$MV"; cd "$MV"; git init -q; echo x > a.txt; git add a.txt; git commit -qm init
git init -q --bare "$T/move-plans.git"
"$LETS" setup --planning private --url "$T/move-plans.git" --plans-dir "$HOME/plans" --check '' --yes </dev/null >/dev/null 2>&1
MP="$HOME/plans/move-plans"
mkdir -p "$MP/epics/shop" "$MP/docs/adr"; echo "# map" > "$MP/epics/shop/map.md"; echo "# 1" > "$MP/docs/adr/0001-one.md"
(cd "$MP" && openspec new change add-thing >/dev/null 2>&1 && git add -A && git commit -qm plans)
"$LETS" setup --planning in-repo --check '' --yes </dev/null >"$T/move.log" 2>&1; rc=$?
check "re-running setup with plans in the repo copies them onto lets-plans, uncommitted" "[ $rc -eq 0 ] && [ \"\$(git rev-parse --abbrev-ref HEAD)\" = lets-plans ] && [ -f plans/epics/shop/map.md ] && [ -f plans/docs/adr/0001-one.md ] && [ -d plans/openspec/changes/add-thing ] && [ -n \"\$(git status --porcelain)\" ]"
check "the old planning repo is untouched, and the repo now uses plans/" "[ -f '$MP/epics/shop/map.md' ] && \"$LETS\" where | grep -q 'plans in this repo'"
check "a clash is asked about, and without a terminal nothing is lost (yours goes beside theirs)" "python3 -c \"
import sys,pathlib,tempfile;sys.path.insert(0,'$REPO/lib')
from lets import move
d=pathlib.Path(tempfile.mkdtemp());(d/'a').mkdir();(d/'b').mkdir()
(d/'a/GLOSSARY.md').write_text('- **Order**: a purchase\n- **Cart**: the basket\n')
(d/'b/GLOSSARY.md').write_text('- **Order**: a purchase\n')
out=move.merge_glossary((d/'b/GLOSSARY.md').read_text(),(d/'a/GLOSSARY.md').read_text(),'nasiq')
assert 'Cart' in out and out.count('**Order**')==1
(d/'b/docs/adr').mkdir(parents=True);(d/'a/docs/adr').mkdir(parents=True)
(d/'b/docs/adr/0003-x.md').write_text('x');(d/'a/docs/adr/0001-y.md').write_text('y')
r=move.adr_renumbering(d/'a',d/'b');assert [p.name for p in r.values()]==['0004-y.md']
\""

echo "branch notes and the status line"
cd "$O"; git checkout -q -b take-card-payment-work
openspec_dir="$O/plans"; (cd "$openspec_dir" && openspec new change take-card-payment >/dev/null 2>&1)
C="$O/plans/openspec/changes/take-card-payment"
printf '# Tasks\n\n## 1. Card form\n\n- [x] 1.1 Build it\n\n## 2. Validate the card number\n\n- [ ] 2.1 Check Luhn\n\n## 3. Charge\n\n- [ ] 3.1 Call the API\n' > "$C/tasks.md"
printf 'schema: spec-driven\nx-lets-epic: shop-checkout\n' >> "$C/.openspec.yaml"
mkdir -p "$O/plans/epics/shop-checkout"; printf '# Shop checkout\n\n## Changes\n- add-catalogue\n- take-card-payment\n- add-gift-cards\n' > "$O/plans/epics/shop-checkout/map.md"
mkdir -p "$O/plans/openspec/changes/archive/2026-11-01-add-catalogue"
SL() { echo '{"workspace":{"current_dir":"'"$PWD"'"}}' | NO_COLOR=1 "$LETS" statusline; }
check "the status line infers the change from the branch name, with epic and task progress" "[ \"\$(SL)\" = 'shop-checkout ●◉○ › take-card-payment ●◉○ › Validate the card number   ✎ pair' ]"
"$LETS" note change take-card-payment --mode agent >/dev/null
check "a branch note sets the change and the mode" "SL | grep -q '⚙ agent' && \"$LETS\" note | grep -qx 'change: take-card-payment'"
perl -pi -e 's/- \[ \]/- [x]/' "$C/tasks.md"
check "a finished change shows what's next instead of a task" "SL | grep -q 'take-card-payment ●●● › next: review'"
"$LETS" note reviewed >/dev/null
check "after review, next is the walkthrough" "SL | grep -q 'next: walkthrough'"
"$LETS" note patch fix-footer-typo >/dev/null
check "a patch shows patch › <name>" "[ \"\$(SL)\" = 'patch › fix-footer-typo   ⚙ agent' ]"
check "outside a LETS branch the status line is empty" "cd '$T' && [ -z \"\$(echo '{\"cwd\":\"$T\"}' | \"$LETS\" statusline)\" ]"
cd "$O"; git checkout -q -; git branch -q -D take-card-payment-work

echo "planning: an OpenSpec change from start to close"
cd "$O/plans"
openspec new change add-order-export >/dev/null 2>&1; C=openspec/changes/add-order-export; mkdir -p $C/specs/order-export
printf '# Proposal\n\n## Why\nShop owners want their orders in a spreadsheet.\n\n## What Changes\n- Add a CSV export of orders.\n\n## Capabilities\n\n### New Capabilities\n- `order-export`: exporting orders as files\n\n### Modified Capabilities\n\n## Impact\nThe orders page and a new endpoint.\n' > $C/proposal.md
printf '## ADDED Requirements\n\n### Requirement: CSV export of orders\nThe system SHALL let a shop owner download the orders shown on the orders page as a CSV file.\n\n#### Scenario: Export the filtered orders\n- **WHEN** the owner filters orders to October and clicks Export\n- **THEN** a CSV file downloads containing only October orders\n' > $C/specs/order-export/spec.md
printf '# Tasks\n\n## 1. Export button and endpoint\n\n- [x] 1.1 Add GET /orders/export (the seam) and verify its test passes\n\n## 2. Filter handling\n\n- [x] 2.1 Export only the filtered orders and verify the filter test passes\n' > $C/tasks.md
check "a change validates --strict" "openspec validate add-order-export --strict"
check "LETS's rules reach OpenSpec's instructions" "openspec instructions tasks --change add-order-export | grep -q 'Each numbered group is one task'"
cd "$O"; git add -A; git commit -qm change
check "a change's files are left out of the walkthrough" "! \"$LETS\" walkthrough scope | grep -q '^plans/'"
cd "$O/plans"
check "closing archives the change and merges its deltas into the specs" "openspec archive add-order-export -y >/dev/null && grep -q 'CSV export of orders' openspec/specs/order-export/spec.md && ls openspec/changes/archive | grep -q 'add-order-export'"
check "dropping archives without touching the specs" "openspec new change try-a-thing >/dev/null 2>&1 && printf '# Tasks\n\n## 1. X\n\n- [ ] 1.1 y\n' > openspec/changes/try-a-thing/tasks.md && openspec archive try-a-thing -y --skip-specs >/dev/null && ls openspec/changes/archive | grep -q 'try-a-thing' && [ ! -e openspec/specs/try-a-thing ]"
cd "$O"

echo "floor check: case corpus"
check "the floor check agrees with all $(python3 -c "import json;print(len(json.load(open('$REPO/tests/floor_cases.json'))))") recorded cases" "python3 '$REPO/tests/floor_cases.py'"

echo "realistic repo (built by the fourth reviewer's fixture)"
cd "$REPO"
RR="$T/realistic"; bash "$REPO/tests/realistic/mkrepo.sh" "$RR" >/dev/null 2>&1
git -C "$RR/shop-tools" config lets.kind own; git -C "$RR/shop-tools" config lets.agents ship  # the daily lists commit and push
check "a day of ordinary work in a monorepo is never blocked" "python3 '$REPO/tests/realistic/allowed.py' '$REPO/agent-hooks/guard.py' '$RR/shop-tools' '$REPO/tests/realistic/daily.txt'"
python3 "$REPO/tests/realistic/allowed.py" "$REPO/agent-hooks/guard.py" "$RR/shop-tools" "$REPO/tests/realistic/daily.txt" | tail -1
GC="$RR/guest-clone"; git clone -q "$RR/origin.git" "$GC"; git -C "$GC" config lets.kind other
check "in a repo that isn't mine, every gh and glab call is blocked, reads included (the fourth tester's tracker list)" "cd '$GC' && python3 -c \"
import json,subprocess,sys
cmds=[c.strip() for c in open(sys.argv[1]).read().split('%%') if c.strip() and c.strip().startswith(('gh ','glab '))]
assert len(cmds) >= 8
for c in cmds:
    r=subprocess.run([sys.executable,sys.argv[2]],input=json.dumps({'tool_name':'Bash','tool_input':{'command':c},'cwd':sys.argv[3]}),universal_newlines=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert r.returncode==2, c
\" '$REPO/tests/realistic/guest.txt' '$REPO/agent-hooks/guard.py' '$GC'"
if git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1; then
  FC="$RR/fork-clone"; git clone -q "$REPO" "$FC" 2>/dev/null; git -C "$FC" checkout -q -b intake/test; git -C "$FC" config lets.kind own
  check "maintainer work inside LETS's own repo is never blocked" "python3 '$REPO/tests/realistic/allowed.py' '$REPO/agent-hooks/guard.py' '$FC' '$REPO/tests/realistic/fork.txt'"
fi
check "three independent testers' diffs each get their recorded outcome (block, ask or nothing)" "python3 '$REPO/tests/realistic/diffs.py' '$REPO/lib' '$RR/origin.git' '$T/diffs'"
python3 "$REPO/tests/realistic/diffs.py" "$REPO/lib" "$RR/origin.git" "$T/diffs" | tail -1
python3 "$REPO/tests/realistic/blind13/run.py" "$REPO/agent-hooks/guard.py" "$T/blind13" >"$T/blind13.log" 2>&1; rc=$?
check "the ninth (blind) tester's guard cases: every ordinary action allowed, every forbidden one blocked or caught where documented" "[ $rc -eq 0 ]"
tail -3 "$T/blind13.log"
check "every plausible mistake the README promises to block is blocked (fourth tester's list)" "bash '$REPO/tests/realistic/attempts.sh' '$REPO/agent-hooks/guard.py' '$RR'"
check "every plausible mistake the README promises to block is blocked (fifth tester's list)" "bash '$REPO/tests/realistic/mistakes.sh' '$REPO/agent-hooks/guard.py' '$RR'"
(cd "$RR/shop-tools" && "$LETS" walkthrough complete >/dev/null)
check "a second day of ordinary work (fifth tester's list, after a walkthrough) is never blocked" "python3 '$REPO/tests/realistic/allowed.py' '$REPO/agent-hooks/guard.py' '$RR/shop-tools' '$REPO/tests/realistic/daily2.txt'"

echo "repos with unusual shapes"
EMP="$T/empty repo"; mkdir -p "$EMP"; (cd "$EMP" && git init -q)
check "an empty repo (no commits) with a space in its path can be set up" "(cd '$EMP' && \"$LETS\" setup --planning in-repo --check '' --yes </dev/null >/dev/null 2>&1) && (cd '$EMP' && \"$LETS\" where | grep -q 'plans in this repo')"
check "the walkthrough says plainly when there are no commits yet" "(cd '$EMP' && \"$LETS\" walkthrough status 2>&1 | grep -qi 'commit')"
TR="$T/trunk-repo"; mkdir -p "$TR"; (cd "$TR" && git init -q -b trunk && echo x > a && git add a && git commit -qm i && git checkout -q -b feat && echo y > b && git add b && git commit -qm b)
check "a repo whose default branch isn't main finds its base" "(cd '$TR' && \"$LETS\" walkthrough scope | grep -q '^b\$')"
SUB="$T/with-sub"; mkdir -p "$SUB"; (cd "$SUB" && git init -q && echo x > a && git add a && git commit -qm i && git -c protocol.file.allow=always submodule add -q "$TR" vendor-lib >/dev/null 2>&1; git commit -qm sub)
check "a repo with a submodule can be set up, and lets check runs" "(cd '$SUB' && \"$LETS\" setup --planning in-repo --check '' --yes </dev/null >/dev/null 2>&1 && \"$LETS\" check >/dev/null)"
CR="$T/crlf"; mkdir -p "$CR/src"; (cd "$CR" && git init -q && printf 'it(\"a\", () => {})\r\n' > src/a.test.ts && git add -A && git commit -qm i && git checkout -q -b f && printf 'it.skip(\"a\", () => {})\r\n' > src/a.test.ts)
check "a skip in a file with Windows line endings is still found" "(cd '$CR' && \"$LETS\" check | grep -q 'skipped test')"

echo "doctor"
check "doctor passes, including this machine's wiring" "\"$LETS\" doctor"
mv "$HOME/.claude/skills/lets" "$HOME/lets-plugin.moved"
check "doctor notices the plugin isn't linked, and fixes it when asked" "! \"$LETS\" doctor </dev/null && \"$LETS\" doctor --yes && [ -L \$HOME/.claude/skills/lets ]"
rm -rf "$HOME/lets-plugin.moved"
python3 - "$CODEX_HOME/hooks.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
for g in d["hooks"]["PreToolUse"]: g["matcher"] = "Edit"
json.dump(d, open(p, "w"))
PY
check "doctor notices a narrowed guard matcher, and puts it right" "! \"$LETS\" doctor </dev/null && \"$LETS\" doctor --yes"
check "doctor passes again" "\"$LETS\" doctor"

echo "uninstall"
"$LETS" uninstall --dry-run >"$T/un.log" 2>&1
check "uninstall --dry-run previews and changes nothing" "grep -q 'Dry run: nothing was changed' '$T/un.log' && [ -L \$HOME/.claude/skills/lets ]"
"$LETS" uninstall --yes >"$T/un.log" 2>&1
check "the plugin and the links are gone" "[ ! -e \$HOME/.claude/skills/lets ] && [ ! -e \$HOME/.local/bin/lets ] && [ ! -e \$HOME/lets ]"
check "your own skill folder is untouched" "[ -f \$HOME/.claude/skills/clash-test/SKILL.md ]"
check "uninstall removes the folders it allowed, and keeps your own settings and status line" "! grep -q '$XDG_DATA_HOME/lets/learning' \$HOME/.claude/settings.json && ! grep -q '$HOME/plans' \$HOME/.claude/settings.json && grep -q my-line.sh \$HOME/.claude/settings.json && grep -q '\"model\"' \$HOME/.claude/settings.json"
check "uninstall keeps your profile, your planning repos and the backups" "[ -f \$XDG_CONFIG_HOME/lets/profile.md ] && [ -d \$HOME/plans/team-app-plans/.git ] && [ -d \$XDG_STATE_HOME/lets/backups ]"
check "the map and hooks are gone, your own CLAUDE.md lines stay" "! grep -q 'lets' \$HOME/.claude/CLAUDE.md && grep -qx '# mine' \$HOME/.claude/CLAUDE.md && ! grep -q guard \$CODEX_HOME/hooks.json"
check "uninstall says how to remove the package" "grep -q 'npm uninstall -g @nasiq/lets' '$T/un.log'"

echo; echo "$pass passed, $fail failed"; rm -rf "$T"; [ "$fail" -eq 0 ]
