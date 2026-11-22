# Think before the question: DABstep as a modeling task

## 1. The task

DABstep is 450 questions about payments and fees. For every question the agent gets the same seven files: a manual (`manual.md`), a thousand fee rules (`fees.json`), reference tables, and a table of 138,236 payments. The answer is a number, a list or a letter; it is checked automatically against a hidden reference.

The difficulty of the tasks is not computational. To answer, one has to connect the text of the manual with the tables: to understand what "monthly fraud level" means, when a rule applies to a payment, how a fee is assembled from the rules. According to the benchmark's authors, at the time of publication the best agent solved 14.55 % of the hard tasks.

## 2. How the task is solved

The solutions published over the lifetime of the benchmark fall into two classes. What separates them is not the number of agents or the choice of language model, but the answer to one question: **when does the system work out the domain**.

**Understanding at question time.** A general-purpose agent receives the question and the files and builds a solution from scratch: it studies the structure of the data, reads the manual, writes code, checks intermediate results and corrects its steps. The improvements of this class — a preliminary analysis of the files, verify-and-fix loops, state kept between steps — raised accuracy on the hard tasks from 15 % to roughly 45–67 % (figures published by the authors of the solutions). Such an agent is not tied to the corpus, but it pays for that: the domain is interpreted anew in every question, and each interpretation may turn out different.

**Understanding before the question.** The system first solves tasks with known answers, generalizes the successful solutions and packs the domain logic into a library of functions. A lightweight model then handles the questions by calling the ready-made functions. The published result of such a solution is about 90 % on the hard tasks, at tens of seconds per question instead of ten minutes.

The comparison leads to a conclusion we agree with and on which our work rests: **accuracy comes from separating the understanding of the domain from answering the question.** Understanding is a separate piece of work, and it is done once.

## 3. In what form the understanding is kept

From here the solutions diverge on **what** the understanding obtained before the question turns into.

In the solutions of the second class it turns into a program: a set of functions written for particular files, their fields and the types of questions encountered. This form has three consequences.

1. **The knowledge is tied to the corpus.** A function that computes a fee knows the column names, the format of `fees.json` and how exactly this manual defines the applicability of a rule. A different set of documents and data means a different library: some tools are rewritten from scratch, the rest are adapted and verified again.
2. **The knowledge is obtained from solved tasks.** The library arises by generalizing solutions checked against known answers. Without a set of tasks with answers for a new domain it cannot be built, and it covers the kinds of questions that occurred in that set.
3. **The knowledge cannot be read as a description of the domain.** The definition of "fraud level" exists as a fragment of code inside a function. A programmer can check it, a domain specialist cannot, and the system cannot be asked what it knows and what it does not.

This is an assessment of the form in which knowledge is kept, not of the quality of other solutions: we judge by the published descriptions, and the results of those solutions are high.

## 4. The boldsea approach: understanding as a model

In the boldsea approach the understanding of the domain is written down not as a program but as a **model in the BSL language** — a description that an engine executes. The solution has three layers, and only two of them depend on the domain.

| Layer | What it is | Depends on the domain |
|---|---|---|
| The BSL language and the engine | Concepts, properties, expressions, conditions; computing values from the loaded facts; queries to the graph | no |
| The domain model | The vocabulary of notions and the rules written as expressions | yes — it is the description of the domain |
| The facts | Reference tables, fee rules, statistics, payment groups | yes — they are the data of the domain |

Hence the differences from a library of functions.

- **The model is built from the documents, not from the tasks.** The corpus contains normative texts — `manual.md` and `fees.json`: definitions, formulas, applicability conditions. Their vocabulary becomes the vocabulary of the model; their rules become its computed properties. Solved tasks are not needed for this.
- **A rule is a fact, not code.** The thousand fee rules are loaded into the graph as individuals. A new rule or a changed rate is a new fact; the model and the queries stay the same. A changed definition is one expression in one place.
- **A change of domain is a new model in the same language.** The engine, the exchange channels and the agent's tools remain as they are: the agent on the graph works with two tools — a query to the graph and a read of the table — and neither of them knows anything about payments. Moving to another domain takes an analyst's work to describe that domain, but not a new system.
- **The model can be read and checked.** It is written in the terms of the domain and can be compared with the manual line by line. It can be asked not only for a value but also whether the value exists (see "The boundary of the known").

The approach is stated in three theses.

1. **Think before the question, not when it arrives.** Understanding the domain is a separate piece of work that does not depend on what will be asked.
2. **Reasoning is a path through a semantic structure, not an inference from raw data.** A rigorous chain over a table and a text is still a chain of interpretations. What makes an answer reliable is a structure in which every fact has a place and every rule has an exact form.
3. **The links must be found before the question.** Which rule applies to which payment, what a fee is made of, which month falls into which tier — all of this is known before the first question and should be recorded, not derived on demand.

## 5. The model on the DABstep corpus

**Vocabulary.** The manual and the reference tables give the notions the domain speaks in: merchant, card scheme, account type, merchant category code (MCC), authorization characteristics indicator (ACI), fee rule, monthly merchant statistics, policy. These are the concepts of the model; there are 12 of them.

**Rules as computations.** What the manual states in words, the model states as expressions:

- the fee of a rule: a fixed part plus a rate on the amount;
- the applicability of a rule: nine fields, where an empty list or a missing value matches any payment;
- the monthly fraud level: fraudulent volume over total volume, not a share of transactions;
- volume and fraud tiers, the capture delay tier, the "intracountry" flag.

The engine computes these values itself when the facts are loaded. The question "which rules apply to the merchant's payments in March" stops being reasoning: the answer is already in the graph as the value of a property.

**Data as facts.** The reference tables, 30 merchants, 1,000 rules and the monthly statistics are loaded into the graph as individuals. The payments themselves stay in the table: the graph holds them not row by row but at the level at which the rules operate — in the form of models. Payments that share the attributes a fee depends on — merchant, scheme, month, credit, ACI, intracountry — form a group; 4,363 groups cover all 138,236 payments, and rule matching is determined once per group.

**The boundary of the known.** The manual contains notions without values: an "excessive fraud level" is named, but no threshold is given. In the model this is a policy without a number, and a conclusion that depends on it does not exist — neither "yes" nor "no". The answer "Not Applicable" is therefore not a guess but a computed state: when a threshold appears, the answer appears. In the same way, the fee of a payment that no rule matches is unknown, not zero.

## 6. The domain model and the reading of a question

The model removes the uncertainty of the domain, but not that of the question's wording. "Which ACI is cheaper" can be read in different ways: sum the fees of the matching rules or take the lowest one; count or not an option in which some payments are left without a rule.

The approach does not hide such forks inside the reasoning; it brings them out. Each reading is an explicit decision, switched by one parameter and producing a separate set of answers. This makes a disagreement with the reference diagnosable: one can see which decision is responsible for which tasks. Three disputed decisions were checked against the public scores of other submissions and confirmed; no answers from that data were copied into the submission.

This is where the honest boundary of the "before the question" thesis lies. The domain model was built before the questions were read and has not changed in substance since. The reading of the wordings was refined on the questions — it is a separate, thin layer on top of the model.

## 7. What came out and what it shows

- Leaderboard (450 tasks, hidden answers): **422 correct, 93.78 %** — easy 98.61 % (71 of 72), hard 92.86 % (351 of 378).
- Of the 28 wrong answers, 23 belong to one task family where the reference is rounded to one or two digits although the task asks for fourteen; our unrounded value is not accepted. This is not a model error, and we did not fit our rounding to the reference.
- Public dev set: 9 of 10.

What exactly this shows has to be stated precisely, because the solution has two paths to an answer, and they are of different kinds.

**The solver.** The answers to the 450 leaderboard tasks are computed by a program: it recognizes the type of question and computes the answer with the same semantics that is written in the model. The model and the solver are checked against each other (200 payments, all groups, control totals), but they are two implementations of one semantics. The solver is tied to the corpus and to the question types of DABstep — in form it is a tool of the same kind as the function libraries of section 3, and domain independence does not extend to it. It shows that the semantics of the model is correct on 450 questions.

**The agent on the graph.** The path "question — query to the model" was checked separately, by an agent that has only the graph and the payments table and no access to the solver, the tasks or the answers:

- public dev set: 9 of 10;
- a sample of 30 hard tasks from the hidden set (random, across all families): 29 of 30 by leaderboard scoring. In all 30 the agent's answer equals the solver's; the single task not credited belongs to the family with the rounded reference.

The agent solved 18 tasks with the graph alone, 9 with the graph and the payments table, and 3 with the table alone. The agent was not run on all 450 tasks. The agent's brief contains the same readings of the wordings as the solver, so the run tests that the model can be executed by queries, not that these readings are independent.

The conclusion is therefore this: the result comes not from the strength of reasoning over a question, but from the fact that the domain is understood once, written down in executable form, and applied in the same way to all questions. What carries over to other domains in this work is exactly this path — the language, the engine, the model and the agent on top of it — not the solver.

## 8. Limits of the approach

- It works where the corpus has a stable domain and formal documents. The more rules and definitions the corpus contains, the larger the gain; on a corpus of unrelated tables alone it is smaller.
- Domain independence is a property of the language, the engine and the way of working, but not of the model: the model of each domain is written anew. In this work the approach was tested on one corpus; portability to another benchmark was not measured here.
- Building the model is an analyst's work, and the quality of the answers is bounded by the quality of the model. An error in the model repeats in all questions at once; on the other hand, it sits in one place and is fixed once.
- The model does not remove the ambiguity of a question — it makes it visible.
