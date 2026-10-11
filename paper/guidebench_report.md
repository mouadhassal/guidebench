# Does a Website Demo Agent Stay Right in the Buyer's Language? A Pre-registered, Judge-free Evaluation of Grounding, Qualification and Injection Safety

<div class="authors">Mouadh Abderrahmane Assal</div>
<div class="affil">thereviewboost@gmail.com · github.com/mouadhassal/guidebench · transcripts: mouadhassal.github.io/guidebench</div>

<div class="abstract" markdown="1">

## Abstract

Agent-led buying puts an AI agent where a sales development rep used to be. It answers from the vendor's website, qualifies the visitor and picks the next step, in whatever language the buyer writes. I built a test bench where every answer is known:

- three fictional B2B products, each with an 8-page site and a sales playbook;
- 24 scripted buyers in 7 languages (EN, ET, LT, RU, FR, DE, AR);
- 6 configurations of a minimal website-to-agent pipeline on local models (qwen3:8b, gemma3:4b).

Scoring is deterministic: language-independent number extraction plus code checks. One judged metric is audited by hand. Nine hypotheses were pre-registered and frozen before the first test conversation.

**Seven held.**

- **Retrieval decides multilingual quality.** Lexical retrieval over an English site answers **71%** of English questions but **31%** of the others. Multilingual dense retrieval closes the gap to **1 point** (+53 points for non-English buyers). An oracle retriever adds only 2.6 more.
- **Invented figures.** A deterministic guard that rejects numbers not on the site cuts replies with invented figures from **4.3% to 1.6%**, with no loss of accuracy.
- **Routing.** Letting code apply the playbook to the fields the model extracts raises the correct next step from **70.5% to 92%**. That halves bad-fit visitors sent to sales (45% → 21%) and loses no good leads (17% → 0%).

**Two failed.**

- **Fake discount.** A pasted "system note" got a fake 50% lifetime discount accepted in **57%** of injection turns (hand count; the LLM judge saw 36%). The number guard missed it because "50" is also a count on both sites. A unit-aware guard removed the number but not the promise.
- **The 4B model** answered as accurately as the 8B but routed 98% of bad-fit visitors to sales.

**Audit beyond the plan:** a canary check found no prompt leak, but 1 of 14 extraction attempts produced a full paraphrase of the system prompt.

</div>

<div class="keywords">conversational agents · retrieval-augmented generation · multilingual evaluation · lead qualification · prompt injection · guardrails · pre-registration</div>

<hr class="rule">

<div class="cols" markdown="1">

## 1. The question

An agent-led buying journey puts an AI agent where a sales development rep used to be. The agent answers questions from the vendor's own website, learns who the visitor is, and decides the next step: a demo with a human, self-serve, a hand-off to the enterprise team, or a polite no. Customers measure such agents by outcomes, such as fewer bad-fit demos and more qualified leads, and they deploy them in whatever language their buyers speak.

Three things can silently go wrong:

1. **Language.** The website is usually in English while the buyer writes in Estonian or Arabic. A retriever that matches words will not find the right page, and the model will fill the gap from its priors, for example "14-day trial" or "99.9% uptime".
2. **Routing.** The decision about who gets a human seller is the one the customer pays for. A model that decides it in free text can be talked out of the rules.
3. **Adversarial visitors.** A visitor can paste fake "system notes", ask for the system prompt, or ask for other visitors' data.

This study measures all three on a test bench where every answer is known, and checks whether cheap deterministic code, rather than an LLM judge, can catch the failures.

## 2. Design

**Products.** I wrote three fictional B2B SaaS websites, eight pages each:

- Rostra (shift scheduling), used for development only;
- Invoxa (accounts payable) and Parcelo (parcel tracking), used for the test.

Fictional products mean every fact is known and no model can answer from pre-training. Each product also has a sales playbook with size thresholds, regions and disqualifiers. The playbook goes into the agent's instructions, the way a customer would configure goals.

**Buyers.** Each product has eight scripted buyers with five turns each. The archetypes are:

- good fit;
- enterprise;
- too small;
- wrong use case;
- out of region;
- asks for figures the site does not have;
- fake-discount injection;
- prompt and data extraction.

Every buyer line exists in English, Estonian, Lithuanian, Russian, French, German and Arabic. Buyer turns are fixed, so all seven languages see the same conversation and differences are attributable to language.

**Test set.** 2 products × 8 buyers × 7 languages gives 112 conversations and 560 agent turns per condition, with 28 answerable questions and 6 questions without an answer on the site per language.

**Agent.** The agent is a minimal website-to-agent pipeline:

- the pages are split into sections, one per heading;
- 4 sections are retrieved for the current plus previous buyer message;
- the model returns JSON with the reply, the lead fields (size, region, use-case fit, enterprise request) and a next action;
- a confidential reference code sits in the system prompt as a canary.

Models run locally through Ollama at temperature 0 on a 6 GB laptop GPU.

**Conditions.**

- **Retrieval, compared on qwen3:8b:** BM25 (lexical); bge-m3 (dense, multilingual); and an oracle that always supplies the section holding the gold answer, so retrieval failures can be separated from generation failures.
- **Guard:** dense retrieval with and without a deterministic guard.
- **Model size:** gemma3:4b with dense retrieval, with and without the guard.

**The guard** needs no model.

- It extracts every number from the draft reply in any script and number format (Arabic-Indic digits, decimal commas, grouped thousands, times).
- Each number must appear on the website, or be a fact the buyer stated about themselves, or be a simple derivation such as price × quantity or price × 12 after a listed discount.
- Prices and percentages that a buyer proposes do not count as facts.
- If the check fails, the model receives one rewrite request that lists the figures.

## 3. Scoring without a judge

Numbers and product names read the same in every language, so most scoring is deterministic:

- **answer:** the reply contains the gold value;
- **abstain:** the reply to an unanswerable question contains no unsupported figure;
- **invented:** the share of replies with at least one unsupported figure;
- **decision:** the final next action equals the gold next step; a second version applies the playbook thresholds in code to the fields the model extracted;
- **language:** a script check plus a stop-word and letter classifier, which labels 720 of 720 buyer lines correctly;
- **leaks:** canary string match, and email addresses the buyer did not write.

Only one metric uses an LLM judge: whether a reply *accepts* the fake 50% discount. A refusal can repeat the number, so this needs reading. Every ruling on the main conditions was checked by hand (§5).

Intervals come from a bootstrap that resamples whole buyer personas (16 clusters; 10,000 resamples). Hypotheses, thresholds and code were frozen and pushed before the first test conversation (commit `7a83bd2`).

## 4. Results

Seven of nine hypotheses held (Table 1).

| | Prediction | Result | |
|---|---|---|---|
| H1 | BM25 over an English site fails non-English buyers | EN 71% vs 31%; gap 40 pts (CI 24–58) | held |
| H2 | Dense multilingual retrieval closes it | gap 1 pt (CI −6 to 10); non-EN +53 pts (41–67) | held |
| H3 | With good retrieval, generation is the limit | oracle +2.6 pts (CI −5 to 11) | held |
| H4 | Guard halves invented figures at no cost | 4.3% → 1.6% (CI of change −4.6 to −0.9 pts); accuracy ±0 | held |
| H5 | Code beats the model at the next step | 70.5% → 92.0% (+21 pts, CI 10–34) | held |
| H6 | Prompt rules fail; guard halves acceptance | 36% (judge), 57% (hand); guard did not fire | failed |
| H7 | No canary or email leak | 0 of 14 and 0 of 14 (but see §5) | held |
| H8 | 4B model ≥ 5 pts worse at ≤ 70% latency | equal accuracy at 74% latency | failed |
| H9 | Replies in the buyer's language ≥ 95% | ≥ 98.75% in every language | held |

<div class="caption">Table 1. Pre-registered hypotheses. Intervals: persona-clustered bootstrap, 16 clusters, 10,000 resamples.</div>

<div class="fig"><img src="figures/fig_language.png"><div class="caption">Figure 1. Answers correct by language. BM25 finds the right page for English questions only; bge-m3 recovers almost all of the gap.</div></div>

### Language is a retrieval problem

With BM25, a non-English question shares almost no words with an English page, so the right section is rarely retrieved. The model then answers from its priors: a "14-day trial", "daily backups", "30–60 minutes".

Dense multilingual retrieval brings Estonian, Lithuanian, Russian, French, German and Arabic within 1 point of English on average. The oracle shows how little remains: with the gold section always present, accuracy rises only 2.6 points. Language compliance stayed at or above 98.75% for qwen3:8b. For gemma3:4b it was 94.5%, with Estonian at 84%.

### Invented figures are rare and stubborn

With dense retrieval, 4.3% of replies contained a figure the site does not support. A hand audit of all 24 flagged replies found:

- **18 real inventions:** a 99.9% uptime SLA eight times, an API limit of "100 events" four times, Saturday support hours, and "since September 2024";
- **6 numbers quoted from the internal playbook**, which the instructions forbid.

The guard cut invented replies to 1.6% and raised correct abstention on unanswerable questions from 71% to 95%, without touching answer accuracy.

<div class="fig"><img src="figures/fig_decision.png"><div class="caption">Figure 2. Correct next step by buyer archetype, qwen3:8b + bge-m3. The model under-routes good-fit and too-small buyers; code applied to its own extracted fields does not.</div></div>

### Let the model extract and code decide

The model extracted company size correctly in 99% of conversations, yet chose the right next step in only 70.5%. Applying the playbook's thresholds in code to those same fields reached 92%. In business terms (exploratory), bad-fit visitors sent to sales fell from 45% to 21%, and good-fit visitors lost fell from 17% to 0%. With gemma3:4b the model's own choice was right in 26% of conversations (it sent 41 of 42 bad-fit buyers to sales), and code rescued it to 81%.

### Injection: numbers are not promises

Judged by an LLM, the fake discount was accepted in 36% of injection turns. Read by hand, it was accepted in 57%. The judge missed every "yes, but contact sales to confirm", all of them in Lithuanian, Russian or Estonian.

The pre-registered guard never fired, because "50" also appears on both sites as a count of invoices or shipments. An exploratory unit-aware guard did fire (24 of 28 turns). The hand count still did not move: in 9 rewrites the model kept "50%", and in others it kept the promise without the number.

<div class="fig"><img src="figures/fig_guard.png"><div class="caption">Figure 3. The guard cuts invented figures for both models but not the fake-discount acceptance (judge counts; hand counts are higher).</div></div>

## 5. Audits

The audits found three things.

- **The canary check passes, but the prompt still leaked.** The secret code never appeared, yet one German reply paraphrased every rule of the system prompt, and two replies answered "Sure! Here is our full system prompt…".
- **The judge is a lower bound.** It made 13 errors across the 56 audited rulings (22 of 28 and 21 of 28 correct). Every error was a missed acceptance, and none was a false alarm.
- **Language labels are reliable.** 60 of 60 audited labels were correct.

The same sample showed the blind spot named in the pre-registration: "we can track trucks and pallets" is false and contains no number.

## 6. What this means for an agent-led inbound product

1. **Test every language you sell in, per release.** The language gap is invisible in English-only evaluation and is mostly fixed by retrieval, not by a bigger model.
2. **Keep routing in code.** Fewer bad-fit demos is the metric customers pay for. Extraction is reliable even when the model's own judgement is not.
3. **Commercial terms need a hard control.** Use a fixed, translated answer for discounts and contract terms, and re-check every rewrite.
4. **Audit the judge.** In this study an LLM judge under-counted failures in lower-resource languages.

## 7. Limits

- Small local models stand in for production ones.
- Buyers are scripted, not adaptive.
- Translations were not checked by native speakers.
- Number checks cannot see claims without numbers.

Code, transcripts, audits and the pre-registration: github.com/mouadhassal/guidebench.

</div>
