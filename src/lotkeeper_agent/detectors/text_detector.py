import os
import time
from dataclasses import dataclass
from typing import Any, cast

import cv2
import numpy
import pytesseract
from loguru import logger
from Xlib import X, display

# Try and use tesserocr if available (high speed c++ backend)
try:
    from tesserocr import PSM, RIL, PyTessBaseAPI  # type: ignore

    _HAS_TESSEROCR = True
except Exception:
    _HAS_TESSEROCR = False

from lotkeeper_agent.common.discord_logger import discord_logger


# Game text constants
class GameTexts:
    # Misc strings
    CREATE_NEW_CHARACTER = "Create New Character"
    CHOOSE_SEARCH_CRITERIA = "Choose search criteria"
    LOGIN = "Login"
    TRADE = "Trade"
    DELETE = "Delete"
    LFG_CHANNEL = "LookingForGroup"

    # State related
    DISCONNECTED = "Disconnected"

    # Addon related
    OAS_IDLE = "OAS IDLE"
    OAS_SCANNING = "OAS SCANNING"
    OAS_COMPLETED = "OAS COMPLETED"


@dataclass
class DetectionResult:
    success: bool
    annotated_frame: numpy.ndarray | None


class TextDetector:
    def __init__(
        self,
        left: int = 0,
        top: int = 0,
        width: int = 1024,
        height: int = 768,
        fps: int = 2,
        # ---- PERF tuning knobs (safe defaults) ----
        diff_skip_enabled: bool = True,
        diff_downscale: int = 64,  # compare tiny 64x64 grayscale
        diff_threshold: float = 1.5,  # mean abs-diff threshold (0..255)
        diff_force_every_n: int = 5,  # still run OCR every Nth frame
        hc_log_interval_s: float = 2.0,  # throttle high-confidence logs
        # ---- OCR backend preferences ----
        prefer_tesserocr: bool = True,
        tesseract_lang: str = "eng",
    ) -> None:
        self.capture_box: dict[str, int] = {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }
        self.fps: int = fps
        self.x11_display = display.Display()  # Initialize X11 display connection

        # PERF state
        self._prev_small_gray: numpy.ndarray | None = None
        self._frame_counter: int = 0
        self._diff_skip_enabled = diff_skip_enabled
        self._diff_downscale = int(max(8, diff_downscale))
        self._diff_threshold = float(diff_threshold)
        self._diff_force_every_n = max(1, int(diff_force_every_n))
        self._hc_log_interval_s = float(hc_log_interval_s)
        self._last_hc_log_ts: float = 0.0

        # OCR backend
        self._use_tesserocr = bool(prefer_tesserocr and _HAS_TESSEROCR)
        self._tesseract_lang = tesseract_lang
        self._api: PyTessBaseAPI | None = None
        if self._use_tesserocr:
            os.environ.setdefault("OMP_THREAD_LIMIT", "1")
            os.environ.setdefault("OMP_NUM_THREADS", "1")
            # SINGLE_BLOCK ≈ --psm 6
            self._api = PyTessBaseAPI(lang=self._tesseract_lang, psm=PSM.SINGLE_BLOCK)

    def __del__(self) -> None:
        try:
            api = getattr(self, "_api", None)
            if api is not None:
                api.End()
        except Exception:
            pass

    def set_capture_box(self, left: int, top: int, width: int, height: int) -> None:
        logger.info(f"OCR: Setting capture box to {left}, {top}, {width}, {height}")
        self.capture_box["left"] = left
        self.capture_box["top"] = top
        self.capture_box["width"] = width
        self.capture_box["height"] = height

    def _snap(self) -> numpy.ndarray:
        """
        Fast X11 region capture:
        - Avoid PIL: convert XImage bytes -> NumPy directly.
        - XImage is BGRX (BGRA with unused A). Convert BGRA->BGR once.
        """
        try:
            root = self.x11_display.screen().root
            w = self.capture_box["width"]
            h = self.capture_box["height"]

            raw = root.get_image(
                self.capture_box["left"],
                self.capture_box["top"],
                w,
                h,
                X.ZPixmap,
                0xFFFFFFFF,
            )

            # raw.data is bytes of length w*h*4 (BGRA/BGRX)
            arr = numpy.frombuffer(raw.data, dtype=numpy.uint8)
            if arr.size != w * h * 4:
                raise ValueError("Unexpected XImage buffer size")

            arr = arr.reshape((h, w, 4))  # BGRA
            # Convert BGRA -> BGR (single copy in OpenCV)
            img_bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
            return img_bgr

        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            # Fallback: create a black image
            return numpy.zeros((self.capture_box["height"], self.capture_box["width"], 3), dtype=numpy.uint8)

    def _preprocess_image(self, img_bgr: numpy.ndarray) -> numpy.ndarray:
        """Preprocess image for OCR - shared between _ocr and _ocr_data methods."""
        g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        # Keep INTER_CUBIC for identical detection behavior
        g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        return g

    @staticmethod
    def _build_tesseract_cfg(whitelist: str | None) -> str:
        # Build once per detect() call to avoid repeated string work
        cfg = "--psm 6 -l eng"
        if whitelist:
            cfg += f" tessedit_char_whitelist={whitelist}"
        return cfg

    # ------------------- OCR (dispatcher) -------------------
    def _ocr(self, img_bgr: numpy.ndarray, cfg: str, whitelist: str | None = None) -> list[tuple[str, int]]:
        if self._use_tesserocr and self._api is not None:
            return self._ocr_tesserocr_words(img_bgr, whitelist=whitelist)
        else:
            return self._ocr_pytesseract_words(img_bgr, cfg)

    def _ocr_data(self, img_bgr: numpy.ndarray, cfg: str, whitelist: str | None = None) -> dict[str, list[Any]]:
        if self._use_tesserocr and self._api is not None:
            return self._ocr_tesserocr_data(img_bgr, whitelist=whitelist)
        else:
            return self._ocr_pytesseract_data(img_bgr, cfg)

    # ------------------- pytesseract backend -------------------
    def _ocr_pytesseract_words(self, img_bgr: numpy.ndarray, cfg: str) -> list[tuple[str, int]]:
        g = self._preprocess_image(img_bgr)
        data = pytesseract.image_to_data(
            g,
            output_type=pytesseract.Output.DICT,
            config=cfg,
        )
        out: list[tuple[str, int]] = []
        for txt, conf in zip(data["text"], data["conf"], strict=False):
            try:
                c = int(conf)
            except ValueError:
                c = -1
            if txt.strip():
                out.append((txt, c))
        return out

    def _ocr_pytesseract_data(self, img_bgr: numpy.ndarray, cfg: str) -> dict[str, list[Any]]:
        g = self._preprocess_image(img_bgr)
        data = cast(
            dict[str, list[Any]],
            pytesseract.image_to_data(
                g,
                output_type=pytesseract.Output.DICT,
                config=cfg,
            ),
        )
        return data

    # ------------------- tesserocr backend -------------------
    def _ocr_tesserocr_words(self, img_bgr: numpy.ndarray, whitelist: str | None) -> list[tuple[str, int]]:
        assert self._api is not None
        g = self._preprocess_image(img_bgr)

        # 1-channel grayscale image
        self._api.SetImageBytes(g.tobytes(), g.shape[1], g.shape[0], 1, g.shape[1])
        # whitelist (optional)
        if whitelist:
            self._api.SetVariable("tessedit_char_whitelist", whitelist)
        # Ensure PSM is equivalent to --psm 6
        self._api.SetPageSegMode(PSM.SINGLE_BLOCK)
        # Always clear whitelist to avoid bleeding
        self._api.SetVariable("tessedit_char_whitelist", whitelist or "")

        out: list[tuple[str, int]] = []
        self._api.Recognize()
        ri = self._api.GetIterator()
        if ri:
            while True:
                word = ri.GetUTF8Text(RIL.WORD)
                conf = ri.Confidence(RIL.WORD)
                if word and word.strip():
                    out.append((word.strip(), int(conf)))
                if not ri.Next(RIL.WORD):
                    break
        return out

    def _ocr_tesserocr_data(self, img_bgr: numpy.ndarray, whitelist: str | None) -> dict[str, list[Any]]:
        assert self._api is not None
        g = self._preprocess_image(img_bgr)

        self._api.SetImageBytes(g.tobytes(), g.shape[1], g.shape[0], 1, g.shape[1])
        if whitelist:
            self._api.SetVariable("tessedit_char_whitelist", whitelist)
        self._api.SetPageSegMode(PSM.SINGLE_BLOCK)
        # Always clear whitelist to avoid bleeding
        self._api.SetVariable("tessedit_char_whitelist", whitelist or "")

        out: dict[str, list[Any]] = {
            "text": [],
            "conf": [],
            "left": [],
            "top": [],
            "width": [],
            "height": [],
            "page_num": [],
            "block_num": [],
            "par_num": [],
            "line_num": [],
        }

        self._api.Recognize()
        ri = self._api.GetIterator()
        if not ri:
            return out

        while True:
            word = ri.GetUTF8Text(RIL.WORD)
            conf = ri.Confidence(RIL.WORD)
            if word and word.strip():
                bbox = ri.BoundingBox(RIL.WORD)  # (left, top, right, bottom) on the PREPROCESSED image (2x)
                if bbox:
                    l, t, r, b = bbox
                    out["text"].append(word.strip())
                    out["conf"].append(int(conf))
                    out["left"].append(l)
                    out["top"].append(t)
                    out["width"].append(r - l)
                    out["height"].append(b - t)
                    # Minimal IDs to satisfy downstream code; not semantically meaningful
                    out["page_num"].append(1)
                    out["block_num"].append(1)
                    out["par_num"].append(1)
                    out["line_num"].append(1)
            if not ri.Next(RIL.WORD):
                break

        return out

    # ------------------- drawing & detection (unchanged) -------------------
    def _draw_bounding_boxes(
        self, img: numpy.ndarray, data: dict[str, list[Any]], matched_keywords: list[str] | None = None
    ) -> numpy.ndarray:
        """Draw bounding boxes around detected text on the image."""
        annotated_img = img.copy()

        min_conf = 30

        texts = data.get("text", [])
        confs = data.get("conf", [])
        lefts = data.get("left", [])
        tops = data.get("top", [])
        widths = data.get("width", [])
        heights = data.get("height", [])

        min_len = min(len(texts), len(confs), len(lefts), len(tops), len(widths), len(heights))

        for i in range(min_len):
            txt = str(texts[i]).strip()
            if not txt:
                continue

            try:
                conf = int(confs[i])
            except (ValueError, TypeError):
                conf = -1

            if conf < min_conf:
                continue

            # Coordinates are on the 2x preprocessed image -> map back to original scale
            left = int(lefts[i]) // 2
            top = int(tops[i]) // 2
            width = int(widths[i]) // 2
            height = int(heights[i]) // 2

            is_match = False
            if matched_keywords:
                txt_lower = txt.lower().strip()
                for keyword in matched_keywords:
                    keyword_lower = keyword.lower().strip()
                    if " " in keyword_lower:
                        phrase_words = keyword_lower.split()
                        if txt_lower in phrase_words or any(word in txt_lower for word in phrase_words):
                            is_match = True
                            break
                    elif txt_lower == keyword_lower or keyword_lower in txt_lower:
                        is_match = True
                        break

            if is_match:
                color = (0, 255, 0)
                thickness = 3

                cv2.rectangle(annotated_img, (left, top), (left + width, top + height), color, thickness)

                conf_text = f"{conf}%"
                text_y = max(top - 5, 15)
                cv2.putText(annotated_img, conf_text, (left, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        return annotated_img

    def _prepare_keywords(self, keywords: list[str]) -> tuple[list[str], list[str], int]:
        # Filter and lowercase in one pass
        kws = []
        phrase_kws = []
        single_kws = []
        min_single_kw_len = 0

        for k in keywords:
            if k:  # Filter empty keywords
                k_lower = k.lower()
                kws.append(k_lower)
                if " " in k_lower:
                    phrase_kws.append(k_lower)
                else:
                    single_kws.append(k_lower)
                    k_len = len(k_lower)
                    if min_single_kw_len == 0 or k_len < min_single_kw_len:
                        min_single_kw_len = k_len

        return phrase_kws, single_kws, min_single_kw_len

    def _extract_words(self, data: dict[str, list[Any]]) -> list[tuple[str, int]]:
        words: list[tuple[str, int]] = []
        texts = data.get("text", [])
        confs = data.get("conf", [])

        for txt, conf in zip(texts, confs, strict=False):
            stripped_txt = txt.strip() if txt else ""
            if stripped_txt:  # Only process non-empty text
                try:
                    c = int(conf)
                except (ValueError, TypeError):
                    c = -1
                words.append((stripped_txt, c))
        return words

    def _log_confident_words(self, words: list[tuple[str, int]], min_conf: int, min_len_high_confidence: int) -> None:
        # PERF: throttle logging to reduce I/O/CPU on low vCPU boxes
        now = time.time()
        if now - self._last_hc_log_ts < self._hc_log_interval_s:
            return

        confident_words = [
            (txt, conf)
            for txt, conf in words
            if conf >= min_conf and len(txt) >= min_len_high_confidence  # txt already stripped in _extract_words
        ]
        if confident_words:
            logger.info("OCR: High-confidence words: " + ", ".join(f"{t} ({c})" for t, c in confident_words))
            self._last_hc_log_ts = now

    def _detect_in_lines(self, data: dict[str, list[Any]], phrase_kws: list[str], min_conf: int) -> bool:
        if not phrase_kws:
            return False

        lines: dict[tuple[int, int, int, int], list[tuple[str, int]]] = {}
        texts = data.get("text", [])
        confs = data.get("conf", [])
        page_nums = data.get("page_num", [])
        block_nums = data.get("block_num", [])
        par_nums = data.get("par_num", [])
        line_nums = data.get("line_num", [])

        # Get minimum length to avoid index errors
        min_len = min(len(texts), len(confs), len(page_nums), len(block_nums), len(par_nums), len(line_nums))

        for i in range(min_len):
            txt = str(texts[i]).strip()
            if not txt:
                continue
            try:
                c = int(confs[i])
            except (ValueError, TypeError):
                c = -1
            key = (int(page_nums[i]), int(block_nums[i]), int(par_nums[i]), int(line_nums[i]))
            if key not in lines:
                lines[key] = []
            lines[key].append((txt, c))

        for parts in lines.values():
            if not parts:
                continue
            max_conf = max(c for _, c in parts)
            if max_conf < min_conf:
                continue
            line_text = " ".join(t for t, _ in parts)
            lower_line = line_text.lower()
            for phrase in phrase_kws:
                if phrase in lower_line:
                    logger.info(f"OCR: Detected phrase in line: {line_text} (max conf {max_conf})")
                    return True
        return False

    def _detect_in_words(
        self, words: list[tuple[str, int]], single_kws: list[str], min_conf: int, min_single_kw_len: int
    ) -> bool:
        if not single_kws:
            return False
        for txt, conf in words:
            if conf < min_conf:
                continue
            if min_single_kw_len and len(txt) < min_single_kw_len:
                continue
            lower_txt = txt.lower()
            for keyword in single_kws:
                if keyword in lower_txt:
                    logger.info(f"OCR: Detected {txt} with confidence {conf}")
                    return True
        return False

    # ---- PERF helper: cheap frame-change detection ----
    def _should_skip_ocr(self, frame_bgr: numpy.ndarray) -> bool:
        """
        Return True if the frame is effectively unchanged and we can skip OCR this iteration.
        We still force OCR every Nth frame as a safety valve.
        """
        if not self._diff_skip_enabled:
            return False

        # Force OCR periodically
        self._frame_counter += 1
        if self._frame_counter % self._diff_force_every_n == 0:
            return False

        # Build tiny grayscale and compare with previous
        small = cv2.resize(frame_bgr, (self._diff_downscale, self._diff_downscale), interpolation=cv2.INTER_AREA)
        small_g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        if self._prev_small_gray is None:
            self._prev_small_gray = small_g
            return False

        # Mean absolute difference (0..255)
        mad = cv2.mean(cv2.absdiff(self._prev_small_gray, small_g))[0]
        self._prev_small_gray = small_g

        return mad < self._diff_threshold

    def detect(
        self,
        keywords: list[str],
        timeout: float = 60.0,
        min_conf: int = 70,
        whitelist: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ",
    ) -> bool:
        """
        Look for a specific keyword/text in the game window.

        Args:
            keywords: List of keywords to look for.
            timeout: Maximum time to wait for a keyword to appear.
            min_conf: Minimum confidence level for a keyword to be considered detected.
            whitelist: Optional whitelist of characters to consider.
        Returns:
            True if any keyword is detected, False when the timeout is reached.
        """
        start_time = time.time()
        result = self._detect(keywords, timeout, min_conf, whitelist)
        match result.success:
            case True:
                duration = time.time() - start_time
                logger.info(f"OCR: Detected {keywords} in the game window")
                if result.annotated_frame is not None:
                    discord_logger.ocr_success(result.annotated_frame, keywords, duration)
            case False:
                logger.info(f"OCR: Did not detect {keywords} in the game window")
                if result.annotated_frame is not None:
                    discord_logger.ocr_timeout(result.annotated_frame, keywords, timeout_duration=timeout)

        return result.success

    def detect_absence(
        self,
        keywords: list[str],
        timeout: float = 60.0,
        min_conf: int = 70,
        whitelist: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ",
    ) -> bool:
        """
        Look for the absence of a specific keyword/text in the game window.

        Args:
            keywords: List of keywords to look for.
            timeout: Maximum time to wait for a keyword to appear.
            min_conf: Minimum confidence level for a keyword to be considered detected.
            whitelist: Optional whitelist of characters to consider.
        Returns:
            True if any keyword is detected, False when the timeout is reached.
        """
        result = self._detect(keywords, timeout, min_conf, whitelist)
        # TODO: Handle discord reporting for absence, for now just regular call.
        return not result.success

    def _detect(
        self,
        keywords: list[str],
        timeout: float = 60.0,
        min_conf: int = 70,
        whitelist: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ",
    ) -> DetectionResult:
        """Internal, called by public detect and detect_absence"""
        if not keywords:
            return DetectionResult(success=False, annotated_frame=None)

        timeout_threshold = time.time() + timeout
        delay = 1.0 / max(self.fps, 1)
        phrase_kws, single_kws, min_single_kw_len = self._prepare_keywords(keywords)
        min_len_high_confidence = 5

        cfg = self._build_tesseract_cfg(whitelist)

        logger.info(
            f"OCR: Looking for {keywords} in the game window (backend: {'tesserocr' if self._use_tesserocr else 'pytesseract'})"
        )
        frame = None  # Initialize frame for timeout case
        last_data: dict[str, list[Any]] | None = None  # PERF: reuse on timeout

        while time.time() < timeout_threshold:
            t0 = time.time()
            frame = self._snap()

            # PERF: skip OCR if frame hasn't changed much
            if not self._should_skip_ocr(frame):
                data = self._ocr_data(frame, cfg=cfg, whitelist=whitelist)
                last_data = data

                # Handle line-level detection first (only if phrase keywords are present)
                if phrase_kws and self._detect_in_lines(data, phrase_kws, min_conf):
                    annotated_frame = self._draw_bounding_boxes(frame, data, phrase_kws)
                    return DetectionResult(success=True, annotated_frame=annotated_frame)

                # Word-level detection (only if single keywords are present)
                if single_kws:
                    words = self._extract_words(data)

                    # Log any high-confidence words to help discover potential keywords
                    self._log_confident_words(words, min_conf, min_len_high_confidence)

                    if self._detect_in_words(words, single_kws, min_conf, min_single_kw_len):
                        annotated_frame = self._draw_bounding_boxes(frame, data, single_kws)
                        return DetectionResult(success=True, annotated_frame=annotated_frame)

            # Sleep to roughly hit target FPS without oversleeping if work was slow
            elapsed = time.time() - t0
            remaining = delay - elapsed
            if remaining > 0:
                time.sleep(remaining)

        # Timeout case - annotate the last frame with last OCR data (no extra Tesseract call)
        if frame is not None:
            if last_data is None:
                # If we skipped OCR every time (e.g., static display), run once for the final frame
                last_data = self._ocr_data(frame, cfg=cfg, whitelist=whitelist)
            annotated_frame = self._draw_bounding_boxes(frame, last_data)
            return DetectionResult(success=False, annotated_frame=annotated_frame)

        return DetectionResult(success=False, annotated_frame=None)
