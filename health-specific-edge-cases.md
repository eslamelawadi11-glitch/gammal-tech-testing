# Health-Specific Edge Cases — Connected Health Ecosystem
**Author:** Eslam Elawadi  
**Date:** 2026-06-25  
**Context:** Gammal Tech Healthcare Platform — Edge cases unique to a connected health ecosystem where wearables, AI, doctors, pharmacies, restaurants, and patient data all talk to each other.
 
---
 
## What Makes Health Edge Cases Different?
 
In a connected health ecosystem, a "bug" isn't just a broken UI — it can delay medication, contradict a doctor, or expose private diagnoses. Every edge case below sits at the intersection of **technical failure** and **real human consequence**.
 
---
 
## Edge Case 01 — Restaurant Sends Calorie Data for a Meal the User Already Cancelled
 
**Scenario:**  
A patient with Type 2 Diabetes uses the app to order a meal from a connected restaurant. They cancel the order 3 minutes after placing it. The restaurant's POS system processes the cancellation, but its nutrition data sync runs on a 15-minute batch job — so the calorie, carb, and sugar data for the cancelled meal gets logged into the patient's health record anyway.
 
**What breaks:**  
- The AI nutrition tracker reports the patient exceeded their daily carb limit
- The daily summary sent to their doctor shows a diet violation that never happened
- Automated dietary alerts fire, possibly triggering a prescription adjustment recommendation
**System boundary hit:**  
Order cancellation system ↔ Nutrition sync pipeline — no cancellation event is passed to the health data layer.
 
**Severity:** High  
**Test:** Cancel order → wait 20 minutes → check health log. Cancelled meal must NOT appear.  
**Expected behavior:** Cancellation event propagates to nutrition service within the same transaction. Health record only updated on confirmed delivery.
 
---
 
## Edge Case 02 — Doctor Cancels Appointment 5 Minutes Before It Starts
 
**Scenario:**  
A patient has driven to the clinic and is in the waiting room. At T-5 minutes, the doctor cancels the appointment from their portal (emergency with another patient). The patient's app shows the appointment as "Upcoming" for another 8 minutes because the notification webhook has a 13-minute polling interval.
 
**What breaks:**  
- Patient waits, confused, while the system still shows the appointment as active
- Automatic check-in is triggered (geofence detects patient at clinic), sending a "patient arrived" ping to the now-absent doctor
- The next available slot algorithm doesn't release the old slot immediately, so other patients can't book it
- If the patient took a medication "1 hour before appointment" (as instructed), and the appointment is cancelled, there's no alert about the now-unnecessary drug timing
**Severity:** High  
**Test:** Cancel appointment via doctor portal at T-5 → measure notification latency on patient device.  
**Expected behavior:** Patient receives push notification within 60 seconds. Slot released immediately. Medication timing alert fires if pre-appointment medication was scheduled.
 
---
 
## Edge Case 03 — AI Prediction Contradicts What the User's Doctor Said
 
**Scenario:**  
A patient asks the in-app AI assistant: "Based on my data, do I have prediabetes?" The AI, trained on the patient's last 90 days of glucose readings from their wearable, returns: "Your glucose patterns suggest a high likelihood of prediabetes. Consider consulting a specialist." The patient's doctor reviewed the same data last week and said: "You're in the normal range, no concern needed."
 
**What breaks:**  
- Patient loses trust in either the AI or their doctor
- Patient may self-medicate or change diet based on AI output without informing doctor
- If the patient shares the AI prediction screenshot with a different doctor, it creates a conflicting paper trail in the medical record
- Liability: who is responsible if the patient acts on the AI and is harmed?
**The deeper problem:**  
The AI has no awareness of what the doctor has already communicated. It treats the data in isolation.
 
**Severity:** Critical  
**Expected behavior:** AI assistant must surface any recent doctor notes or conclusions before making predictions on the same data. If a doctor assessment exists within 30 days, AI response should include: *"Your doctor reviewed similar data on [date] and noted: [summary]. My analysis is for informational purposes only."*
 
---
 
## Edge Case 04 — Wearable Loses Sync During a Critical Vitals Window
 
**Scenario:**  
A post-surgery patient is being monitored at home via a connected wearable (heart rate, SpO2, temperature). The wearable loses Bluetooth sync for 40 minutes while the patient is sleeping — exactly the window when their heart rate spikes to 130 BPM and SpO2 drops to 91%. When the device reconnects, it uploads the buffered data, but the alert thresholds only evaluate **real-time** incoming values, not retroactively replayed buffer data.
 
**What breaks:**  
- The critical alert that should have woken the on-call nurse never fires
- The event is visible in the historical graph but no one was notified
- Post-incident review shows the system "worked" — it just didn't alert because the data arrived late
**Severity:** Critical  
**Test:** Simulate 40-minute sync gap with threshold-crossing data → confirm alert fires on buffer replay.  
**Expected behavior:** Alert engine must evaluate all incoming data regardless of timestamp. If a buffered reading crosses a threshold, alert fires with timestamp of the original event and a flag: *"Delayed alert — data received [X] minutes after event."*
 
---
 
## Edge Case 05 — Two Doctors Prescribe Conflicting Medications Simultaneously
 
**Scenario:**  
A patient sees their cardiologist and their GP in the same week. Both use the platform. The cardiologist prescribes Warfarin (blood thinner). The GP, looking at a slightly stale view of the patient's record (cached 6 hours ago, before the cardiology appointment was finalized), prescribes Aspirin the next morning. Both are blood thinners — taking them together carries serious bleeding risk.
 
**What breaks:**  
- The drug interaction checker runs at prescription time, but the cardiologist's prescription wasn't in the system yet when the GP's session loaded
- The pharmacy receives both prescriptions and dispenses both — their system checks interactions but only flags it as "low concern" because it sees them as separate orders from different doctors
- No cross-doctor conflict alert is sent
**Severity:** Critical  
**Test:** Submit conflicting prescriptions from two doctor accounts within a 10-minute window → verify drug interaction alert fires before second prescription is confirmed.  
**Expected behavior:** Real-time drug interaction check must query live prescription state, not a cached snapshot. Second prescribing doctor sees a blocking alert: *"Patient is already prescribed [Drug A] by [Dr. X] on [date]. [Drug A] + [Drug B] interaction: HIGH RISK."*
 
---
 
## Edge Case 06 — Patient's Health Goal Changes Mid-Meal Plan Cycle
 
**Scenario:**  
A patient sets a goal: "Lose 5kg in 3 months." The nutrition AI generates a 4-week meal plan. On day 18, the patient's doctor updates their goal in the system to "Maintain weight — patient is recovering from illness." The meal plan continues running on the old goal. The calorie targets, macros, and weekly check-in messages are all still optimized for weight loss — which is now medically contraindicated.
 
**What breaks:**  
- The meal plan service holds its own goal state, copied at plan-generation time
- Doctor's update only touches the `patient_goals` table, not the `active_meal_plans` table
- Patient receives a message: "You're 300 calories over your weight loss target today!" when they should be eating more
**Severity:** High  
**Test:** Update patient goal mid-plan → verify active meal plan recalculates within same session.  
**Expected behavior:** Goal change event triggers immediate recalculation of all active plans. Patient receives notification: *"Your health goal was updated by Dr. [Name]. Your meal plan has been adjusted."*
 
---
 
## Edge Case 07 — Appointment Reminder Sent to a Deceased Patient's Next of Kin
 
**Scenario:**  
A patient passes away. The hospital updates the patient's status in the EMR system to "Deceased." However, the appointment reminder service runs on a separate microservice with its own scheduled-appointments table, synced nightly. A follow-up appointment booked before the patient's death is still in the queue. The next morning, an automated SMS reminder is sent to the patient's phone — which is now held by their grieving spouse.
 
**What breaks:**  
- Severe emotional harm to the family
- HIPAA implication: the message may contain appointment details (department name, doctor name) that reveals the nature of the patient's illness to whoever has the phone
- The appointment slot remains blocked, denying it to another patient
**Severity:** Critical  
**Test:** Mark patient as deceased → verify all future appointments are cancelled and reminder queue is flushed within 1 hour.  
**Expected behavior:** Patient status change to "Deceased" must propagate synchronously — not in a nightly batch — to all downstream services: reminders, meal plans, wearable monitoring, prescription refills.
 
---
 
## Edge Case 08 — Pharmacy Marks Prescription as "Picked Up" Before Patient Arrives
 
**Scenario:**  
A pharmacy staff member scans the prescription bag to "stage" it for pickup — a common workflow to move it from the dispensing queue to the pickup shelf. The platform interprets the scan event as "prescription collected" and closes the prescription in the patient's record. The patient arrives 20 minutes later, picks up the medication, but the system already sent a "medication taken — start tracking adherence" notification. The adherence tracker now thinks the patient took their first dose 20 minutes ago, and schedules the next reminder accordingly — off by one dose.
 
**What breaks:**  
- Medication adherence tracking is offset from the start
- If the medication requires dose-timing precision (e.g., antibiotics every 8 hours), every subsequent reminder is wrong
- Doctor's adherence dashboard shows a false "on schedule" status
**Severity:** Medium  
**Test:** Simulate "staged" scan vs. actual pickup scan → verify adherence tracking only starts on confirmed patient pickup, not pharmacy staging.  
**Expected behavior:** Distinguish between `STAGED_FOR_PICKUP` and `CONFIRMED_COLLECTED` events. Adherence tracking starts only on the latter, confirmed by patient acknowledgment in the app.
 
---
 
## Edge Case 09 — Timezone Change Breaks Medication Schedule for a Travelling Patient
 
**Scenario:**  
A patient on a strict medication schedule (e.g., immunosuppressants every 12 hours) flies from Cairo (UTC+2) to London (UTC+1). The app stores reminder times as local device time. When the phone automatically adjusts to UK time, all future medication reminders shift 1 hour earlier in absolute time — so the patient's "9:00 PM dose" now fires at what is biologically 8:00 PM Cairo time. Over a week, this drifts the medication window by 7 hours from the original schedule.
 
**What breaks:**  
- Medication reminders are no longer aligned with the medically prescribed interval
- For time-sensitive medications (e.g., HIV antiretrovirals, transplant immunosuppressants), even a 1-2 hour drift can reduce efficacy
- The doctor's adherence view shows "compliant" because the patient took every dose — just not at the right biological times
**Severity:** High  
**Test:** Change device timezone mid-schedule → verify reminder times recalculate based on prescribed interval from last dose, not wall-clock time.  
**Expected behavior:** Medication schedules stored in UTC. On timezone change, patient receives: *"You've changed timezone. Your next [Medication] dose is due at [local time] — [X] hours from your last dose. Tap to confirm or adjust."*
 
---
 
## Edge Case 10 — AI Chatbot Gives a Confident Answer Based on an Outdated Medical Guideline
 
**Scenario:**  
A patient asks the AI health assistant: "What's the recommended daily sodium intake for someone with mild hypertension?" The AI, trained on data up to 18 months ago, confidently answers "2,300 mg/day" — which was the WHO guideline at training time. The guideline was updated 8 months ago to 1,500 mg/day for hypertensive patients specifically. The patient has been following the AI's advice, consuming 800mg more sodium daily than their condition currently warrants.
 
**What breaks:**  
- The AI presents outdated clinical guidance as current fact with no uncertainty signal
- No "last updated" or "guideline source" is shown to the patient or doctor
- The patient's blood pressure management has been subtly undermined for months
- If the doctor later asks "did you follow dietary advice?", the patient truthfully says yes — but the advice was wrong
**The deeper problem:**  
Static AI models in a dynamic clinical world are a structural mismatch. Medical guidelines update continuously.
 
**Severity:** High  
**Test:** Query AI with a clinical question whose guideline changed in the last 12 months → verify response includes source date and uncertainty flag.  
**Expected behavior:** AI health responses must include: source citation, guideline version/date, and a standard disclaimer: *"Medical guidelines change. This information is based on [source] as of [date]. Always confirm with your healthcare provider."* High-stakes clinical queries (medication dosing, dietary limits for chronic conditions) should trigger an automatic "verify with your doctor" prompt.
 
---
 
## Cross-Cutting Observations
 
These 10 cases share **3 systemic failure patterns:**
 
**1. Eventual consistency in a real-time health world**  
Batch syncs, caching, and polling intervals create windows where the system believes a state that is no longer true. In healthcare, a 13-minute polling lag isn't a UX annoyance — it's a missed critical alert.
 
**2. Service isolation without event propagation**  
Each microservice (nutrition, reminders, prescriptions, adherence) holds its own copy of patient state. A change in one service (goal update, death status, appointment cancellation) must propagate synchronously to all dependents, not via nightly ETL.
 
**3. AI confidence without clinical context**  
The AI assistant operates on data, not on the clinical conversation that has already happened. Without awareness of recent doctor assessments, active prescriptions, and guideline recency, confident AI output can actively mislead patients.
 
---
 
*Part of the Gammal Tech Testing Suite — `gammal-tech-testing` repo*
 
