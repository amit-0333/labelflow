# Experiment: label quality and the effect of AI pre-labeling

This document explains **where every number in the README comes from**, exactly how it is computed, and how to run the study that produces the real values.

> The worked examples below use made-up numbers, only to show the arithmetic. They are not results. The real results go in the table in section 6.

## 1. Questions the study answers

| # | Question | Metric |
|---|---|---|
| 1 | Do human annotators agree with each other beyond chance? | Cohen's kappa |
| 2 | How often do people accept the AI suggestion? | AI acceptance rate |
| 3 | Does seeing the AI suggestion make labeling faster? | Time per label, with vs without AI |
| 4 | Can the platform catch careless or wrong labels? | Gold answers, too-fast labels |

## 2. Setup

| Item | Choice |
|---|---|
| Dataset | `sample_data/emails.csv` (120 emails), plus a gold file with known answers |
| Annotators | 3 to 4 people with their own accounts, annotator role |
| Reviewer | 1 person, reviewer role |
| AI model | The value of `GROQ_MODEL` in `.env`. Write it down. |
| Annotators per item | 2 (project setting) |
| Gold questions | Rows with a `gold_label`, shown to every annotator and hidden among normal tasks |
| Groups | Half of the annotators have the AI suggestion **on**, half **off** (Users page, Toggle) |

Everything runs inside the app, and the numbers come from the same database the annotators wrote to.

## 3. How each value is computed

### 3.1 Cohen's kappa (human vs human)

**Idea:** raw agreement overstates quality, because two people guessing at random still agree some of the time. Kappa removes the agreement expected by chance.

**Formula**

```
p_o   = share of tasks where both people chose the same label
p_e   = sum over labels of (share A chose it) x (share B chose it)
kappa = (p_o - p_e) / (1 - p_e)
```

**Where:** `cohens_kappa()` in `quality/agreement.py`, shown on the Agreement page.

**What is compared**
- Every pair of annotators, on the normal tasks both of them labeled.
- The AI against each annotator (the AI label is the latest prediction for the task).
- Gold questions are excluded.
- The page also lists the number of tasks compared and the plain agreement percentage.

**Worked example (made-up numbers)**

Two people label 4 emails:

| Email | A | B |
|---|---|---|
| 1 | spam | spam |
| 2 | spam | not spam |
| 3 | not spam | not spam |
| 4 | not spam | not spam |

- `p_o` = 3 / 4 = 0.75
- A chose spam 50% and not spam 50%. B chose spam 25% and not spam 75%.
- `p_e` = 0.5 x 0.25 + 0.5 x 0.75 = 0.5
- `kappa` = (0.75 - 0.5) / (1 - 0.5) = **0.5**

**How to read it:** below 0.4 weak, 0.4 to 0.6 moderate, 0.6 to 0.8 good, above 0.8 very strong. If both people use only one label, kappa cannot be calculated and the page shows `n/a`.

**Most confused labels:** for every task where two humans disagreed, the label pair is counted. The table shows which pairs are mixed up most.

### 3.2 AI acceptance rate

**Definition:** among labels where the AI suggestion was shown, the share where the human chose the same label.

```
acceptance = labels equal to the AI suggestion / labels shown a suggestion
```

**Where:** every label stores `accepted_ai` (`True`, `False`, or empty when no suggestion was shown). `get_project_stats()` in `quality/stats.py` reads it, and the Dashboard shows it.

**Only counted:** normal tasks, and only annotators whose AI switch is on. Gold questions never show a suggestion.

**Worked example (made-up numbers):** 100 labels were shown a suggestion and 80 matched it. Acceptance = 80 / 100 = **80%**.

**Important caveat, anchoring:** people tend to accept what is shown to them, so acceptance can overstate how good the AI is. The cleaner check is the **AI vs annotator kappa** for annotators who had the suggestion switched **off**, because their labels were not influenced. Report both.

### 3.3 Time per label, with vs without AI

**What is measured:** the page records the time from the moment the task is shown to the moment a label button is pressed (`time_taken_ms`). That includes reading time.

**Groups**
- **With AI:** labels where the suggestion was shown.
- **Without AI:** labels on tasks that have an AI prediction, where the annotator's switch was off.

Only tasks that have a prediction are used for both groups, so the two groups label the same kind of task. Gold questions are excluded.

```
avg_with      = mean time of labels with the suggestion
avg_without   = mean time of labels without it
time saved %  = (avg_without - avg_with) / avg_without x 100
```

**Where:** `get_project_stats()` in `quality/stats.py`, shown on the Dashboard. The script in section 5 also prints the median.

**Worked example (made-up numbers):** with AI 4.5 s, without AI 6.0 s. Time saved = (6.0 - 4.5) / 6.0 = **25%**. A negative value means the suggestion slowed people down.

**Why it needs care**
- Run **AI pre-labeling before anyone starts labeling.** Without predictions, the tasks are excluded from the comparison.
- Annotators must read each item. Pressing keys without reading gives near-identical times in both groups, which tells you nothing.
- The mean is sensitive to outliers, such as someone who leaves a tab open. Compare it with the median.

### 3.4 Bad labels caught by quality checks

Reported as three separate counts, because they are different kinds of evidence.

| Count | Definition | Where |
|---|---|---|
| Wrong gold answers | Gold question where the label differs from `gold_label`, out of all gold answers given | Dashboard, Quality page |
| Too-fast labels | Labels made in under 1 second (`FAST_MS = 1000` in `quality/scores.py`) | Dashboard, Quality page |
| Reviewer overruled | Tasks where annotators disagreed and the reviewer decided | Dashboard |

A too-fast label is suspicious but not automatically wrong, so do not add the counts into one number without saying so.

**Annotator weight** (Quality page): `gold accuracy x (1 - share of labels under 1 second)`. Example (made-up): 4 of 5 gold answers correct and 10% of labels too fast gives 0.8 x 0.9 = **0.72**. The weight is shown, but it is not yet used to weight votes.

## 4. Protocol

1. **Prepare the data.** Upload `emails.csv`. Also upload a file with **at least 10 gold rows** (`text,gold_label`). Two gold questions are too few to score anyone.
2. **Create accounts.** Each annotator registers, and the reviewer registers. On the Users page, set the reviewer's role. Toggle the AI switch to `no` for half of the annotators.
3. **Run AI pre-labeling first.** On the project page, click **Run AI pre-labeling** and wait until **AI pre-labeled** equals the number of tasks.
4. **Brief everyone.** Read every item before labeling. Do not rush. Use the number keys. Work alone, without talking about the answers.
5. **Label.** Each annotator labels until the page says there are no tasks left.
6. **Review.** The reviewer clears the review queue.
7. **Collect the numbers** (section 5).
8. **Freeze the data.** On the Versions page, click **Create new version**, so the study dataset is saved as v1.
9. **Take screenshots** of the Dashboard, the Agreement page and the Quality page.
10. **Fill the table** in section 6 and the README.

## 5. Collecting every number in one command

`scripts/study_results.py` prints all the values above for one project.

With Docker (the project id is on the project page URL, `/project/<id>`):
```powershell
docker compose exec web python scripts/study_results.py 1
```

Without Docker:
```powershell
python scripts/study_results.py 1
```

It prints progress, acceptance, mean and median time with and without the suggestion, the gold and too-fast counts, the kappa table, the most confused labels, and the annotator scores. The numbers are read from the same functions the dashboard uses, so they match the pages.

## 6. Results

Fill this in after the study.

| Field | Value |
|---|---|
| Date | |
| Annotators (AI on / AI off) | |
| Reviewer | |
| Items | |
| Gold questions | |
| Model (`GROQ_MODEL`) | |

| Metric | Value |
|---|---|
| Kappa, human vs human (per pair) | |
| Kappa, AI vs annotator, AI-off annotators | |
| Kappa, AI vs annotator, AI-on annotators | |
| AI acceptance rate | |
| Mean time per label, with AI | |
| Mean time per label, without AI | |
| Median time per label, with / without AI | |
| Time saved | |
| Wrong gold answers | |
| Labels under 1 second | |
| Tasks decided by the reviewer | |
| Most confused label pair | |

**Summary for the README** (three lines, once the table is filled):

> N annotators labeled N items. Human kappa was X, and the AI agreed with AI-off annotators at kappa X. Annotators accepted the AI suggestion on X% of labels, and labeling took X% less / more time with it. The quality checks flagged X wrong gold answers and X labels under one second.

## 7. Limitations of this study

- **Small sample.** A few friends and a few hundred labels give wide uncertainty. Report the counts next to every percentage.
- **Easy dataset.** Synthetic spam emails are easy, so agreement and acceptance will look high. A harder dataset would be more informative.
- **Anchoring.** Showing a suggestion changes what people choose. See the AI-off comparison in 3.2.
- **Uncontrolled task mix.** Tasks go to whoever asks first, so the AI-on and AI-off groups do not label exactly the same items. Random order evens this out, but only roughly.
- **Timer noise.** Reading time, distractions and a first-label warm-up all end up in the timing.
- **Few gold questions.** Accuracy scores are only meaningful with enough gold rows.
- **Friends are not domain experts.** Their agreement says little about expert annotation.

Report the study with these limits stated. Honest numbers from a small study are worth more than impressive numbers that cannot be reproduced.