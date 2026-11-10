# 會考練習卷 — project notes for Claude

A practice site for Taiwan's 國中教育會考. The user (a parent, pei) set it up for their child, who uses it on a tablet.
Reply to the user in Traditional Chinese (Taiwan), plainly, with no jargon. The user is not an engineer.

## What the site does
- It is a static site served by GitHub Pages from `docs/`. There is no login and no backend.
- Each subject has one mixed question bank:
  - official 會考 questions from 104–115
  - 阿克提供 questions written by Claude (阿克 is the user's name for Claude)
- 102–103 are not included because they are scanned PDFs. 108 English is also missing.
- Each test draws at random the same number of questions as the real exam:
  - 國文 42
  - 英語閱讀 43 (reading only)
  - 數學 25 (multiple-choice only; the real exam also has 2 written questions)
  - 社會 54
  - 自然 50
- How a test is drawn:
  - unseen questions come first
  - a 題組 (group of questions sharing a passage) is drawn whole
  - single questions come first, then groups
- 錯題區 (wrong-question pool), one per subject:
  - a wrong or unanswered question goes in and is left out of random draws
  - it leaves only after **2 consecutive correct** answers inside the 錯題區
- State is kept in the tablet browser's localStorage (key `cap-quiz-v1`).
  - Keep that key and its data shape (`seen/wrong/cur/hist/wa`; `wa` records the last answers, used by 瀏覽錯題) backward-compatible, or the child loses records.
  - A 備份碼 (backup code) on the page exports and imports that state.
- After a test is submitted:
  - each question shows its explanation if it has one
  - an easy question (pass rate 60% or higher) with no explanation shows a short "basic question" note
  - any other question without one shows 「詳解補充中」 ("explanation coming")
  - the grade estimate uses the 115 cutoffs
- The PDF button uses jsPDF from cdnjs and downloads a PDF of the current test with an answer key.

## Layout
- `docs/index.html` is GENERATED. Never edit it by hand. Run `python3 tools/build.py`.
- `docs/pk/{year}_{subject}.wasm` are image packs, not real wasm: lossless WebP images concatenated together.
  - The extension is `.wasm` only so hosts serve the file raw.
  - The index of each pack lives in `data/questions.json` → `packs[pk][imgName] = [offset, length, w, h]`.
- `data/questions.json` holds the official questions, each like `{id:"113-math-12", y, n, img, pk, ans, pimg?, grp?}`.
  - `pimg` is the passage image.
  - `grp` is the group id, like `113-chinese-34～35`.
- `data/explanations/{year}/{subject}.json` maps question number → explanation text: `{"12": "…"}`. **This is where new explanations go.**
- `data/meta/{year}.json` holds official analysis data: `{subject: {n: {goal, pr}}}`.
  - `pr` is the national pass rate in percent.
  - Only 114 and 115 have it so far.
- `data/ak/{subject}_{k}.json` holds 阿克 question sets:
  - each has `{subject, qs: [{n, html, opts[4], ans, exp, topic, grp?, passage?}]}`
  - a new set goes in `{subject}_2.json` and so on; its ids become `ak2-...`
- `tools/template/` holds the page source: `head.html` (CSS), `extra.css`, and `body.html` (all JS; `__BANK__` is replaced with the data).
- `tools/show.py`:
  - `python3 tools/show.py 113 math` exports every question image of 113 math to `/tmp/show/*.png` and prints the answers.
  - `python3 tools/show.py 113-math-12` exports one question.
  - Read the PNGs to see the questions. Needs Pillow.

## Ongoing task: write explanations, newest year first
The user's rule is 「簡單的 pass，困難的再提供，一年一年補」: skip easy questions, write explanations for hard ones, one year at a time.

Done so far:
- 115 and 114 (all questions)
- every 阿克 question

Next, in order:
- 113, 112, 111, … 104
- for each year, all five subjects

How to write one year:
1. Run `python3 tools/show.py <year> <subject>` and Read each PNG. The official answer is printed; never change it.
2. Choose which questions are hard:
   - Use `pr < 60` when meta data exists.
   - Otherwise judge it: multi-step reasoning, a calculation, a reading or diagram trap, or a commonly confused concept counts as hard.
   - In practice that is about 30–50% of the questions.
3. Write the explanation:
   - 2–4 short sentences in Traditional Chinese, for a 9th grader.
   - Say why the correct option is right.
   - Where it helps, say briefly why the tempting wrong option(s) are wrong, like `(A)…；(C)…`.
   - Do not restate the answer letter at the start; the page already shows `(X)`.
   - Plain text only, no HTML.
   - Use full-width punctuation.
4. Add the entries to `data/explanations/<year>/<subject>.json`.
5. Run `python3 tools/build.py`. It validates the data and must print `OK`.
6. Check one page in a browser if you can.
7. Commit and push. GitHub Pages redeploys in about 1–2 minutes.
8. Tell the user in one or two sentences which year and subjects were added.

Accuracy matters more than speed. If you are unsure about a question, re-read the image carefully, or leave it without an explanation.

## Other possible work (only if the user asks)
- A math 非選擇題 (written questions) practice area: show the image plus the official scoring guide, with no scoring.
  - Source papers and scoring guides are at https://cap.rcpet.edu.tw/ under 歷屆試題.
- More 阿克 question sets, written in the style of the official questions.
- Grade cutoffs are in `CUT` in `body.html` (the 115 table).
