# GearMatch narrated demonstration

[Watch or download the MP4](https://raw.githubusercontent.com/Chaiporn2005/gearmatch-mouse/main/docs/demo/GearMatch-demo.mp4)

Thai narration, approximately 5 minutes 36 seconds. The MP4 contains optional Thai subtitles and eight chapter markers. External [Thai subtitles](GearMatch-demo.th.srt) and the [full transcript](NARRATION.th.md) are included.

This is an edited walkthrough using **actual UI stills** from the working local app and technical cards generated from measured repository data. It is **not a continuous screen recording**. Narration is synthetic Thai speech (Google Thai via gTTS), not the student's recorded voice. Subtitle phrase timing is editorial and approximate. These production choices are disclosed in the opening narration.

The successful recommendation and the no-match answer were obtained from the real class proxy with `gemma-4-E4B-it`. No saved response JSON was substituted into the application. The captured DOM transcripts preserve those outcomes. No API key or proxy URL appears in the captures.

## Edited cut

[GearMatch-demo-edit.mp4](GearMatch-demo-edit.mp4) is a faster re-edit of the same walkthrough, about 5 minutes 34 seconds. It reuses the original narration audio and UI captures. Long pauses are shortened, the camera moves to the part of each capture being described, and Thai captions are burned in. It adds a short opening montage, chapter cards and a soft synthesized music bed.

Chapters 04–06 are animated cards that show the same measured numbers as the original technical cards. No app response or measurement is changed. The closing card repeats the disclosure about edited stills and synthetic narration.

Rebuild with `python scripts/edit_demo.py` (needs ffmpeg, Pillow, numpy and Google Chrome for Thai typesetting). Add `--no-music` to leave out the music bed.

## Contents

1. Product problem and the 21-SKU corpus.
2. Quiet office Bluetooth mouse under USD 30: real recommendation.
3. Manufacturer evidence and comparison with a more expensive alternative.
4. A deliberate no-match case with explicit constraints.
5. Tool loop, filters, ranking and answer validation.
6. Real retrieval baseline, ablation and hybrid results.
7. A historical software failure and the recorded repair result.
8. Limitations and reproducibility.

The displayed historical 3/3 smoke result is a small recorded suite, not a new general reliability claim. The planned no-match case is distinguished from the earlier software failure. USD prices are manufacturer reference prices; the Cobra price is dated launch MSRP.

## Rebuild

The build uses the committed UI captures and measured data. It does not automate or recreate browser interactions.

```bash
python -m pip install Pillow gTTS==2.5.4
# ffmpeg and ffprobe must be on PATH.
# The script's font paths use the standard macOS Arial fonts.
python scripts/build_demo.py --speed 1.3
```

Only the public narration text is sent to Google's TTS service. Application secrets are never used by the demo builder. Local intermediate audio and frames are ignored under `.demo-build/`. `manifest.json` records the UI commit, duration, chapters and video SHA-256.

The owner should review the content against the course's requirements before submission, particularly whether the instructor expects the student's own voice or a continuous recording.
