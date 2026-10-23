# solution — sanity-check-3 (static, R2 attachment)

Walkthrough, so review can verify the intended path:

1. On the challenge page under **Files**, download `gifts.zip`
   (served from the attachments bucket, not the challenge repo).
2. List the archive *before* extracting: `unzip -l gifts.zip` shows
   `README.txt` and `gifts/gift-7.txt` — while the README says there were
   only 5 crates. Trust the listing, not the cover letter.
3. Extract and read `gifts/gift-7.txt`:
   `ingehack{bucket_list_checked_twice}` (fixed; shared).
4. Submit it on the platform.

Solver one-liner:

```sh
unzip -p gifts.zip gifts/gift-7.txt
```
