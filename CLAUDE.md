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
  - about 70% from the 108 curriculum (111 and later, plus all 阿克 questions) and 30% from 104–110; a 「只出新課綱題目」 checkbox (`st.opt.newOnly`) limits draws to 111+ and 阿克
  - unseen questions come first
  - a 題組 (group of questions sharing a passage) is drawn whole
  - single questions come first, then groups
- 錯題區 (wrong-question pool), one per subject:
  - a wrong or unanswered question goes in and is left out of random draws
  - it leaves only after **2 consecutive correct** answers inside the 錯題區
- State is kept in the tablet browser's localStorage (key `cap-quiz-v1`).
  - Keep that key and its data shape (`seen/wrong/cur/hist/wa/opt`; `wa` records the last answers, used by 瀏覽錯題) backward-compatible, or the child loses records.
  - A 備份碼 (backup code) on the page exports and imports that state.
- After a test is submitted:
  - each question shows its explanation if it has one
  - an easy question (pass rate 60% or higher) with no explanation shows a short "basic question" note
  - any other question without one shows 「詳解補充中」 ("explanation coming")
  - every official question also shows a 難度 chip (`lv`, computed in `tools/build.py`):
    - with pass-rate data (114, 115): 基礎 (pr 60+), 中等 (40–59), 較難 (below 40)
    - other years: 中等以上 if it has an explanation, 基礎 if not (Claude's own judgement, because a year-subject whose explanation file exists has already been screened)
    - a 基礎 question with no explanation says it is a basic question, so the child does not think the explanation is missing
    - 「詳解補充中」 now shows only for a year-subject that has no explanation file yet
    - 阿克 questions have no chip
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
- `data/ak/{subject}_{k}.json` holds 阿克 question sets (`_1` = basic set, `_2` = 素養題 in the style of 108-curriculum questions: real-life contexts, tables, long reading). HTML `<table>` is allowed in `html`/`passage`.

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

## Adding a new year (for example 116, after that year's exam)
The tools are in `tools/crop/`. They need Python with `pymupdf`, `pillow` and `numpy` (`pip install pymupdf pillow numpy`), plus `pdftotext` (poppler) for `parse_ana.py`. `work/` is git-ignored scratch space.

1. Download the official PDFs from https://cap.rcpet.edu.tw/ (歷屆試題). The browser may be needed, because the site can block scripts.
2. Save them in `work/y116/pdf/` with these names:
   - `answer.pdf` (the 參考答案)
   - `chinese.pdf`, `english.pdf` (閱讀), `math.pdf`, `social.pdf`, `science.pdf`
   - optionally the 試題分析 PDFs as `ana_chinese.pdf`, `ana_english.pdf`, and so on (these hold the pass rates)
3. Run `python3 tools/crop/build_year.py 116`.
   - It reads the answer key, crops each question and each 題組 passage into `work/img/116_*.png`, and writes `work/y116/items.json`.
   - If a paper fails, it prints `SKIP`. For a subject whose paper PDF is too big or broken, crop from the analysis PDF instead: `python3 tools/crop/crop_ana.py 116 social`.
4. **Check the crops.** Open a good sample of `work/img/116_*.png`. Look for figures that are cut off, a question that includes part of the next one, or a passage merged into a question.
   - `crop.py` has many layout rules learned from 104–115; a new year's layout may need a small tweak.
   - The question count must match the answer key: 國文 42, 英語閱讀 43, 社會 54, 自然 50, and the math multiple-choice count (25 or 26).
5. Run `python3 tools/crop/add_year.py 116`. It writes `docs/pk/116_*.wasm` and adds the questions to `data/questions.json`.
6. Optionally run `python3 tools/crop/parse_ana.py 116`. It writes `data/meta/116.json` (pass rates and goals).
7. Update `CUT` in `tools/template/body.html` to the new year's 等級 cutoff table if the user wants. Also update the year range shown in the header text of `body.html`.
8. Run `python3 tools/build.py`, check the site in a browser, then commit and push. Then write explanations for the new year as described above.

The tools were tested by re-cropping 110: the output was byte-identical to the published packs.
