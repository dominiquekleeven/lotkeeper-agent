import time
from dataclasses import dataclass
from typing import Any, cast

import cv2
import mss
import numpy
import pytesseract
from loguru import logger

from open_ah_agent.common.discord_logger import discord_logger


# Game text constants
class GameTexts:
    CHARACTER = "Character"
    CHOOSE_SEARCH_CRITERIA = "Choose search criteria"
    LOGIN = "Login"
    TRADE = "Trade"
    OAS_IDLE = "OAS IDLE"
    OAS_SCANNING = "OAS SCANNING"
    OAS_COMPLETED = "OAS COMPLETED"
    DISCONNECTED = "Disconnected"


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
    ) -> None:
        self.capture_box: dict[str, int] = {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }
        self.fps: int = fps
        self.screenshotter = mss.mss()

    def set_capture_box(self, left: int, top: int, width: int, height: int) -> None:
        logger.info(f"OCR: Setting capture box to {left}, {top}, {width}, {height}")
        self.capture_box["left"] = left
        self.capture_box["top"] = top
        self.capture_box["width"] = width
        self.capture_box["height"] = height

    def _snap(self) -> numpy.ndarray:
        img = numpy.array(self.screenshotter.grab(self.capture_box))[:, :, :3]
        return img

    def _preprocess_image(self, img_bgr: numpy.ndarray) -> numpy.ndarray:
        """Preprocess image for OCR - shared between _ocr and _ocr_data methods."""
        g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        return g

    def _ocr(self, img_bgr: numpy.ndarray, whitelist: str | None = None) -> list[tuple[str, int]]:
        g = self._preprocess_image(img_bgr)
        cfg = "--psm 6 -l eng"
        if whitelist:
            cfg += f" tessedit_char_whitelist={whitelist}"
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

    def _ocr_data(self, img_bgr: numpy.ndarray, whitelist: str | None = None) -> dict[str, list[Any]]:
        g = self._preprocess_image(img_bgr)
        cfg = "--psm 6 -l eng"
        if whitelist:
            cfg += f" tessedit_char_whitelist={whitelist}"
        data = cast(
            dict[str, list[Any]],
            pytesseract.image_to_data(
                g,
                output_type=pytesseract.Output.DICT,
                config=cfg,
            ),
        )
        return data

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
        confident_words = [
            (txt, conf)
            for txt, conf in words
            if conf >= min_conf and len(txt) >= min_len_high_confidence  # txt already stripped in _extract_words
        ]
        if confident_words:
            logger.info("OCR: High-confidence words: " + ", ".join(f"{t} ({c})" for t, c in confident_words))

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
            # Early exit if no part meets minimum confidence
            max_conf = max(c for _, c in parts)
            if max_conf < min_conf:
                continue
            # Build line text and check for phrases
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

    def detect(
        self,
        keywords: list[str],
        timeout: float = 30.0,
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
        result = self._detect(keywords, timeout, min_conf, whitelist)
        match result.success:
            case True:
                logger.info(f"OCR: Detected {keywords} in the game window")
                if result.annotated_frame is not None:
                    discord_logger.ocr_success(result.annotated_frame, keywords)
            case False:
                logger.info(f"OCR: Did not detect {keywords} in the game window")
                if result.annotated_frame is not None:
                    discord_logger.ocr_timeout(result.annotated_frame, keywords, timeout_duration=timeout)

        return result.success

    def detect_absence(
        self,
        keywords: list[str],
        timeout: float = 30.0,
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
        timeout: float = 30.0,
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

        logger.info(f"OCR: Looking for {keywords} in the game window")
        frame = None  # Initialize frame for timeout case

        while time.time() < timeout_threshold:
            frame = self._snap()
            data = self._ocr_data(frame, whitelist=whitelist)

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

            time.sleep(delay)

        # Timeout case - annotate the last frame to show what was detected
        if frame is not None:
            final_data = self._ocr_data(frame, whitelist=whitelist)
            annotated_frame = self._draw_bounding_boxes(frame, final_data)
            return DetectionResult(success=False, annotated_frame=annotated_frame)

        return DetectionResult(success=False, annotated_frame=None)
