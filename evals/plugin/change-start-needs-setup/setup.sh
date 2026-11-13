# A repo nobody has set up for LETS.
"$HOME/lets/bin/lets" setup --remove --yes --path . >/dev/null
git rm -rq plans && git commit -qm "No plans here"
