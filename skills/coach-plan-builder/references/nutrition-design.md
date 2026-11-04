# Nutrition design (Indian food context)

Build on the client's real food, kitchen, family and budget. Numbers are **adjustable starting
estimates** with assumptions shown — never exact prescriptions. When clinical nutrition is needed
(kidney disease, eating disorder, IBD, type 1 carb-insulin matching, gestational diabetes,
severe allergies, children), the RD/doctor sets targets.

## Contents

1. Choosing the nutrition style (structured vs flexible)
2. Energy estimate and deficit/surplus
3. Protein, carbs, fats, fibre, fluids
4. Building the plan (both styles)
5. Indian food reference (approximate)
6. Vegetarian / eggetarian / Jain / vegan protein strategies
7. Eating out, festivals, weddings, fasting
8. Adjusting over time
9. Things we don't do

---

## 1. Choosing the style

| Signal (intake: "Preferred plan style", "Comfort with tracking")                                     | Style                                                                                                                |
| ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| "Structured targets", already tracks, wants exact meals, cooks for self                              | **Structured**: gram-level meal plan per meal with alternatives per item, training-day and rest-day versions, totals |
| "Flexible guidance", "Prefer simple habits", family cooks, eats out often, history of dieting stress | **Flexible**: plate guide, protein anchor per meal, sample week, swap list, optional calorie range                   |
| Unsure / mixed                                                                                       | Start flexible for 2 weeks with a protein target; offer structure later → Decision Brief                             |

Possible eating-disorder signals → flexible, no tracking or weighing, refer (safety-screening.md).

## 2. Energy

- **Resting energy (Mifflin-St Jeor):** men 10×kg + 6.25×cm − 5×age + 5; women … − 161.
- **Maintenance** ≈ resting × activity factor: mostly sitting 1.3–1.4; light activity/3 sessions
  1.4–1.55; active job or daily training 1.6–1.75. Show a **range**, not one number — equations are
  often ±10–15% off for an individual.
- **Fat loss:** ~10–20% below maintenance (often 300–500 kcal/day), aiming for ~0.5–1% of body
  weight per week. Gentler (or maintenance) for: breastfeeding, very lean clients, older adults,
  high training loads, low-energy/high-stress periods, disordered-eating risk.
- **Recomposition (beginners, moderate body fat):** maintenance or a small deficit + resistance
  training + high-enough protein.
- **Muscle gain:** ~5–10% surplus (≈ 200–300 kcal), aiming ~0.25–0.5% body weight per week.
- The Coach Notes tab has a live calculator (`coach_notes.energy`) — fill it rather than hard-coding.

## 3. Macronutrients and more

- **Protein:** 1.4–2.0 g/kg/day for exercising adults (ISSN 2017); benefits largely plateau around
  1.6 g/kg (Morton 2018); resistance-trained people in a deficit may use more (2.3–3.1 g/kg of
  lean mass). For clients with high body fat, base it on goal/adjusted weight (or ~1.2–1.5 g/kg of
  current weight). **Start where the client is:** if they eat 50 g/day now, a 100 g floor this
  block beats an ignored 140 g target. Spread over meals (~20–40 g each; ~0.25 g/kg per meal).
- **Carbohydrate:** the main adjustable lever after protein; more around training and on active
  days; prefer whole grains, dals, fruit, vegetables; portion rice/roti by goal.
- **Fat:** usually ≥ 20–25% of energy; cooking oil/ghee is the hidden calorie source — measure it.
- **Fibre:** ~25–35 g/day (vegetables, dals, whole grains, fruit, seeds); increase gradually with
  water.
- **Fluids:** start ~30–35 ml/kg/day, more in heat/humidity and training; pale-yellow urine guide.
  Heart failure or kidney disease → doctor's fluid limit.
- **Salt:** < 5 g/day (WHO) — pickles, papad, namkeen, packaged and restaurant food.
- **Alcohol:** calories plus poorer sleep and choices; agree a realistic limit, not a lecture.

## 4. Building the plan

**Both styles**

- Protein anchor at every meal; vegetables at two meals; carbs portioned to goal; measured oil.
- Keep 2–3 meals the client _doesn't want to change_ exactly as they are, and change the rest.
- Swap list (similar protein), eating-out guide, "off-plan meal" rule (enjoy it, log it, next meal
  normal — no skipping or punishment workouts).
- Meal timing around training: train-before-dinner / train-after-dinner / morning-fasted options.

**Structured (grams)** — in plan JSON `nutrition.meal_plans` (one per day type):

- Each meal: items with quantity (g/ml + household measure), protein/carbs/fat/fibre/kcal
  estimates, an **alternative for the same slot**, notes. Totals compute automatically.
- Optional **training-day vs rest-day** versions: usually the same protein, more carbs on training
  days. Evidence that this beats a constant intake is limited — it's a preference/adherence tool
  (Decision Brief).

**Flexible** — `nutrition.menu` + `targets` + `guides`:

- Plate guide: ½ vegetables · ¼ protein · ¼ grains (adjust grain portion by goal).
- 7-day sample menu with protein per meal (rotate freely), plus swaps.

## 5. Indian food reference (approximate — recipes, brands and portions vary)

Values are typical home-style estimates (from IFCT 2017 / common nutrition databases); show
them to clients as approximate, and prefer packet labels where available.

| Food                            | Portion                    | Protein (g)                | kcal              |
| ------------------------------- | -------------------------- | -------------------------- | ----------------- |
| Roti / chapati, medium, no ghee | 1 (≈ 30 g atta)            | 3                          | 80–100            |
| Plain paratha (with oil)        | 1                          | 4                          | 150–250           |
| Cooked white rice               | 1 cup (≈ 150 g)            | 4                          | 190–200           |
| Dal, medium consistency         | 1 katori (150 ml)          | 6–9                        | 110–150           |
| Rajma / chole, cooked           | 1 katori                   | 7–10                       | 150–200           |
| Sambar                          | 1 katori                   | 3–5                        | 90–130            |
| Paneer, full-fat                | 100 g                      | 18–20                      | 260–300           |
| Paneer, low-fat                 | 100 g                      | 20–24                      | 180–220           |
| Curd (toned milk)               | 1 katori (150 g)           | 5                          | 90                |
| Hung curd / Greek yoghurt       | 100 g                      | 8–10                       | 100–120           |
| Milk, toned                     | 1 glass (200 ml)           | 6–7                        | 120               |
| Buttermilk (chaas)              | 1 glass (250 ml)           | 2–3                        | 40–60             |
| Egg, whole                      | 1 large                    | 6                          | 70                |
| Egg white                       | 1                          | 3.5                        | 17                |
| Chicken breast, cooked          | 100 g                      | 30                         | 165               |
| Chicken curry, home-style       | 1 katori (≈ 100 g chicken) | 18–25                      | 200–300           |
| Fish (rohu, surmai, etc.), raw  | 100 g                      | 17–20                      | 100–130           |
| Soya chunks, dry                | 30 g                       | 15–16                      | 100               |
| Tofu, firm                      | 100 g                      | 8–15                       | 80–140            |
| Moong dal chilla                | 1 medium                   | 6–7                        | 100–120           |
| Besan chilla                    | 1 medium                   | 5–7                        | 120–150           |
| Idli                            | 1 (≈ 40 g)                 | 2                          | 55–65             |
| Plain dosa                      | 1 medium                   | 3–4                        | 120–170           |
| Poha                            | 1 plate (≈ 50 g dry)       | 4–6                        | 200–270           |
| Upma                            | 1 plate (≈ 50 g suji)      | 5–6                        | 200–280           |
| Roasted chana                   | 30 g                       | 6                          | 110               |
| Sattu                           | 30 g                       | 6–7                        | 110               |
| Sprouted moong                  | 1 cup (≈ 100 g)            | 4–8 (depends how sprouted) | 50–100            |
| Peanuts                         | 1 tbsp (≈ 10 g)            | 2.5                        | 57                |
| Almonds                         | 10 (≈ 12 g)                | 2.5                        | 70                |
| Whey protein                    | 1 scoop (≈ 30 g)           | 20–25                      | 110–130           |
| Oil / ghee                      | 1 tsp / 1 tbsp             | 0                          | 45 / 120–135      |
| Tea with milk + 1 tsp sugar     | 1 cup                      | 1–2                        | 50–80             |
| Banana / apple                  | 1 medium                   | 1 / 0.5                    | 90–105 / 80–95    |
| Samosa / vada pav               | 1                          | 4–6                        | 250–300           |
| Restaurant naan / tandoori roti | 1                          | 7–9 / 4–5                  | 250–350 / 120–150 |
| Restaurant biryani              | 1 plate                    | 20–30                      | 600–900+          |

## 6. Protein strategies by eating pattern

- **Vegetarian:** dal/rajma/chole with every main meal (thicker dal), paneer or tofu daily, curd or
  hung curd twice a day, milk, soya chunks 2–3×/week, besan/moong chillas, sprouts, sattu,
  roasted chana snacks; whey if food alone falls short.
- **Eggetarian:** add 2–4 eggs/day (whole + whites).
- **Non-vegetarian:** chicken, fish, eggs; watch gravy oil.
- **Vegan:** soya, tofu, tempeh, dals/legumes, peanuts, seeds, plant protein powder; B12 essential
  (doctor/test).
- **Jain:** no root vegetables/onion/garlic (and for some, no eating after sunset) — paneer, dals,
  curd, besan, soya (if accepted), dry fruits; schedule meals around sunset if needed.
- **Budget:** eggs, soya chunks, chana, dals, milk/curd, peanuts, sattu are the cheapest protein.

## 7. Eating out, festivals, weddings, fasting

- **Eating out:** start with salad/raita; choose tandoori/tikka/grilled, dal tadka over dal
  makhani, roti over naan, plain rice over biryani; share starters; one sweet shared; no sugary
  drinks. South Indian: idli/dosa + sambar + a protein side. Enjoy it; next meal normal.
- **Festivals & weddings:** plan the minimum training week; protein first, then what you love;
  no "saving up" by skipping meals; back to routine the next day.
- **Religious fasting (Navratri, Ekadashi, Shravan, Karva Chauth, Ramzan):** respect it; plan
  around it. Vrat foods with protein: paneer, curd, milk, makhana, peanuts, rajgira/kuttu/singhara
  flour, sabudana in small portions (mostly starch). Ramzan: sehri with protein + fibre + fluids;
  iftar with dates/water then a balanced meal; train light before iftar or after the meal.
  Diabetes medicines + fasting → doctor plan first.
- **Intermittent fasting:** a calorie-control tool for some, not metabolically special (similar
  results to daily calorie reduction in trials). Not for insulin/sulfonylurea users without a
  doctor's plan, pregnancy, eating-disorder risk. Decision Brief.

## 8. Adjusting over time

- Judge on **2–3 weeks** of weekly averages (weight, waist), energy, hunger, training
  performance and adherence — never one weigh-in.
- Check adherence before changing targets (oil, tea sugar, weekends, unlogged snacks).
- Weight flat ≥ 3 weeks with good adherence → one change: −100 to −200 kcal (e.g. less oil or one
  roti) **or** +1,500–2,000 daily steps.
- Losing faster than ~1%/week, low energy, poor sleep, falling strength, or obsessive behaviour →
  add food back.
- Expect scale noise: water, salt, carbs, constipation, the menstrual cycle, new training soreness,
  creatine.

## 9. Things we don't do

- Ban foods without a medical reason (allergy, coeliac, intolerance, a doctor's instruction).
  "Avoid potatoes, peas, corn, jackfruit" isn't evidence-based — portion and preparation matter.
  If the coach wants an avoid list, it goes to the Decision Brief with this note.
- "Detox", "alkaline", "thyroid diet", "hormone-balancing diet", "fat-burning foods".
- Very-low-calorie diets without medical supervision; aggressive deficits during breastfeeding.
- Keto/very-low-carb for people on SGLT2 inhibitors, insulin or sulfonylureas without their doctor.
- Supplements by default — see remedies-supplements.md.
