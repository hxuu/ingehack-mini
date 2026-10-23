# solution — sanity-check-2 (static, local attachment)

Walkthrough, so review can verify the intended path:

1. On the challenge page, under **Files**, download `naughty-list.zip`.
2. Unzip: `unzip naughty-list.zip` (or right-click → extract in the file
   manager).
3. Read `naughty-list.txt` inside — the flag is the first line:
   `ingehack{naughty_but_readable}` (fixed; shared — the attachment is the
   same file for every team).
4. Submit it on the platform.

Solver one-liner:

```sh
unzip -p naughty-list.zip naughty-list.txt | head -1
```
