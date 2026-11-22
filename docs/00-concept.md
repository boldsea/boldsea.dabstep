# Think before the question: DABstep as a modeling task

## Where the approach comes from

DABstep is 450 questions about payments and fees. For every question the agent gets the same seven files: a manual (`manual.md`), a thousand fee rules (`fees.json`), reference tables, and a table of 138,236 payments. According to the benchmark's authors, at the time of publication the best agent solved 14.55 % of the hard tasks.

The cause is not weak logic. The agent receives a question and only then starts to work out the domain: it rereads the manual, decides again what "monthly fraud level" means and when a rule applies to a payment, joins the tables again. Each of these steps is an interpretation, and an error in any one of them makes the whole answer wrong. There are 450 questions and one domain — and the understanding of that domain is rebuilt from scratch every time, each time slightly differently.

Three theses follow, and the work rests on them.

1. **Think before the question, not when it arrives.** Understanding the domain is a separate piece of work. It is done once and does not depend on what will be asked.
2. **Reasoning is a path through a semantic structure, not an inference from raw data.** A rigorous chain over a table and a text is still a chain of interpretations. What makes an answer reliable is a structure in which every fact has a place and every rule has an exact form.
3. **The links must be found before the question.** Which rule applies to which payment, what a fee is made of, which month falls into which tier — all of this is known before the first question and should be recorded, not derived on demand.

To these theses we add an observation about the corpus itself: **it contains formal documents that do not need to be understood every time — they can be translated once into an executable model.** `manual.md` and `fees.json` are normative texts: definitions, formulas, applicability conditions. Their vocabulary becomes the vocabulary of the model; their rules become its computed properties.

## What this means on the DABstep corpus

**Vocabulary.** The manual and the reference tables give the notions the domain speaks in: merchant, card scheme, account type, merchant category code (MCC), authorization characteristics indicator (ACI), fee rule, monthly merchant statistics, policy. These are the concepts of the model; there are 12 of them.

**Rules as computations.** What the manual states in words, the model states as expressions:

- the fee of a rule: a fixed part plus a rate on the amount;
- the applicability of a rule: nine fields, where an empty list or a missing value matches any payment;
- the monthly fraud level: fraudulent volume over total volume, not a share of transactions;
- volume and fraud tiers, the capture delay tier, the "intracountry" flag.

The engine computes these values itself when the facts are loaded. The question "which rules apply to the merchant's payments in March" stops being reasoning: the answer is already in the graph as the value of a property.

**Data as facts.** The reference tables, 30 merchants, 1,000 rules and the monthly statistics are loaded into the graph as individuals. The payments themselves stay in the table: the graph holds them not row by row but at the level at which the rules operate — in the form of models. Payments that share the attributes a fee depends on — merchant, scheme, month, credit, ACI, intracountry — form a group; 4,363 groups cover all 138,236 payments, and rule matching is determined once per group.

**The boundary of the known.** The manual contains notions without values: an "excessive fraud level" is named, but no threshold is given. In the model this is a policy without a number, and a conclusion that depends on it does not exist — neither "yes" nor "no". The answer "Not Applicable" is therefore not a guess but a computed state: when a threshold appears, the answer appears. In the same way, the fee of a payment that no rule matches is unknown, not zero.

## The domain model and the reading of a question

The model removes the uncertainty of the domain, but not that of the question's wording. "Which ACI is cheaper" can be read in different ways: sum the fees of the matching rules or take the lowest one; count or not an option in which some payments are left without a rule.

The approach does not hide such forks inside the reasoning; it brings them out. Each reading is an explicit decision, switched by one parameter and producing a separate set of answers. This makes a disagreement with the reference diagnosable: one can see which decision is responsible for which tasks. Three disputed decisions were checked against the public scores of other submissions and confirmed; no answers from that data were copied into the submission.

This is where the honest boundary of the "before the question" thesis lies. The domain model was built before the questions were read and has not changed in substance since. The reading of the wordings was refined on the questions — it is a separate, thin layer on top of the model.

## What came out

- Leaderboard (450 tasks, hidden answers): **422 correct, 93.78 %** — easy 98.61 % (71 of 72), hard 92.86 % (351 of 378).
- Of the 28 wrong answers, 23 belong to one task family where the reference is rounded to one or two digits although the task asks for fourteen; our unrounded value is not accepted. This is not a model error, and we did not fit our rounding to the reference.
- Public dev set: 9 of 10.

What exactly this shows has to be stated precisely. The answers to the 450 tasks are computed by a solver: it recognizes the type of question and computes the answer with the same semantics that is written in the model. The model and the solver are checked against each other (200 payments, all groups, control totals), but they are two implementations of one semantics. The path "question — query to the graph" was checked separately, by an agent that has only the graph and the payments table and no access to the solver, the tasks or the answers:

- public dev set: 9 of 10;
- a sample of 30 hard tasks from the hidden set (random, across all families): 29 of 30 by leaderboard scoring. In all 30 the agent's answer equals the solver's; the single task not credited belongs to the family with the rounded reference.

The agent solved 18 tasks with the graph alone, 9 with the graph and the payments table, and 3 with the table alone. The agent was not run on all 450 tasks. The agent's brief contains the same readings of the wordings as the solver, so the run tests that the model can be executed by queries, not that these readings are independent.

The conclusion is therefore this: the result comes not from the strength of reasoning over a question, but from the fact that the domain is understood once, written down in executable form, and applied in the same way to all 450 questions.

## Limits of the approach

- It works where the corpus has a stable domain and formal documents. The more rules and definitions the corpus contains, the larger the gain; on a corpus of unrelated tables alone it is smaller.
- Building the model is an analyst's work, and the quality of the answers is bounded by the quality of the model. An error in the model repeats in all questions at once; on the other hand, it sits in one place and is fixed once.
- The model does not remove the ambiguity of a question — it makes it visible.
