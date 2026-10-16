# Acquisition and manual annotation protocol

## Prepare

1. Record camera model, Pi model, OS, camera stack, resolution, requested rate, lighting and footwear in the session notes. Use participant codes instead of names.
2. Fix the camera on a stable support, side-on, showing the entire body and both feet against a contrasting floor/background. Avoid occlusion and camera motion.
3. Check lighting and foot visibility with a short test capture. In capture mode, requested settings are 640×480, 30 fps; delivered timing must be inspected. Imported higher-rate recordings may reduce temporal quantization if their capture timing is trustworthy.
4. Record one CMJ: still stance, countermovement, one jump, landing and brief still stance. Use consistent arm/hand instructions and footwear across your study. Record first, analyse afterward.

## Annotate

1. Import or capture; wait for processing. Confirm participant/session and that the sample is not marked DEMO when collecting real data.
2. Step frame by frame near takeoff. Select the **last frame showing any foot-ground contact**. Next frame must show both feet airborne. Heel rise while toes remain on the ground is still contact.
3. Step near landing. Select the **first frame showing any foot-ground contact**. Previous frame must show both feet airborne. Use earliest contact if feet land at different times.
4. Inspect both neighbouring pairs using Previous/Next and each event card's Inspect control. Frame indices start at zero.
5. Open diagnostics. Inspect timestamp provenance, ordering/gaps and event intervals. Container PTS are playback timestamps; establish that they represent elapsed capture time. Do not accept a nominal fps label alone as evidence.
6. Check posture, blur, foot visibility and unusual gaps. If contact is ambiguous, select the ambiguity checkbox, add a note and leave Unreviewed or Reject. Do not invent an exact contact time.
7. Check contact and timing confirmations, then Mark reviewed. Save notes. Export the trial ZIP and session CSV.

## Evaluate the chain on real hardware

- Record repeated short clips and measure import/processing time, responsiveness, peak memory if possible, storage per trial and dropped/irregular intervals on the Pi 3B+.
- Compare two blinded annotators' event frame selections/intervals. Report disagreement in frames and milliseconds, and agreement in flight-time estimates. Visual agreement is not independent criterion validity.
- Use a synchronized independent measurement method (e.g. a suitable force platform/contact reference) to assess event timing and flight time. Document synchronization, the reference event definition and its uncertainty. Validate height separately if required.
- If adding a detector, tune on a declared training/development set and evaluate on separate recordings. Preserve unmodified proposals; report missing detections, error distribution and manual correction frequency. Never forward-fill missing contacts silently.
- Collect no performance or accuracy claim from the bundled animated sample. It tests software behaviour only.
