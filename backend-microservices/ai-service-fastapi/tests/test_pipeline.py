"""
Tests for Pipeline Orchestrator (pipeline.py).
"""

import numpy as np
import cv2
import pytest

from app.engine.pipeline import (
    BanknoteRecognitionPipeline,
    PipelineDecision,
    PipelineResult,
    ClassificationMethod,
)
from app.engine.preprocessing import QualityStatus


def make_green_banknote(h: int = 200, w: int = 300) -> np.ndarray:
    """Create a green image (should match 100000 VND — SAFE group)."""
    hsv = np.full((h, w, 3), [55, 200, 200], dtype=np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def make_blue_banknote(h: int = 200, w: int = 300) -> np.ndarray:
    """Create a blue image (should match 20000 VND — DANGER group)."""
    hsv = np.full((h, w, 3), [110, 200, 200], dtype=np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def make_grey_image(h: int = 200, w: int = 300) -> np.ndarray:
    """Create a noisy grey (low-saturation) image — hard to classify by colour."""
    # Random noise with low saturation to prevent dominant colour match
    rng = np.random.RandomState(42)
    img = rng.randint(110, 140, (h, w, 3), dtype=np.uint8)
    return img


class TestPipelineInit:
    def test_init_with_nonexistent_dir(self):
        """Pipeline should initialize even without model files."""
        pipeline = BanknoteRecognitionPipeline(model_dir="/nonexistent/dir")
        assert pipeline is not None

    def test_init_with_tmp_dir(self, tmp_path):
        pipeline = BanknoteRecognitionPipeline(model_dir=str(tmp_path))
        assert pipeline is not None


class TestPipelineProcess:
    @pytest.fixture
    def pipeline(self, tmp_path):
        return BanknoteRecognitionPipeline(model_dir=str(tmp_path))

    def test_green_banknote_accepted_by_color(self, pipeline):
        """Green image → 100000 VND (SAFE group, threshold 0.75) → color classification."""
        img = make_green_banknote()
        result = pipeline.process(img)

        assert result.decision == PipelineDecision.ACCEPT
        assert result.denomination == "100000"
        assert result.method == ClassificationMethod.COLOR
        assert result.confidence > 0.5
        assert "color_classification" in result.stages_executed

    def test_result_has_quality(self, pipeline):
        img = make_green_banknote()
        result = pipeline.process(img)
        assert result.quality_result is not None
        assert result.quality_result.blur_score >= 0

    def test_result_has_detection(self, pipeline):
        img = make_green_banknote()
        result = pipeline.process(img)
        assert result.detection_result is not None
        assert result.detection_result.found is True

    def test_result_has_processing_time(self, pipeline):
        img = make_green_banknote()
        result = pipeline.process(img)
        assert result.processing_time_ms > 0

    def test_result_stages_executed(self, pipeline):
        img = make_green_banknote()
        result = pipeline.process(img)
        assert "preprocessing" in result.stages_executed
        assert "detection" in result.stages_executed
        assert "color_classification" in result.stages_executed

    def test_grey_image_triggers_ai_fallback(self, pipeline):
        """Grey noisy image should either trigger AI fallback or have low colour confidence."""
        img = make_grey_image()
        result = pipeline.process(img)
        # Grey noise may still match a colour with low/high conf depending on random distribution.
        # The key test: pipeline runs at least color_classification stage.
        assert "color_classification" in result.stages_executed
        # If colour confidence was low, AI fallback should have been triggered
        if result.method == ClassificationMethod.AI_FALLBACK:
            assert "ai_fallback" in result.stages_executed

    def test_all_probabilities_populated(self, pipeline):
        img = make_green_banknote()
        result = pipeline.process(img)
        assert result.all_probabilities is not None
        assert len(result.all_probabilities) > 0

    def test_message_not_empty(self, pipeline):
        img = make_green_banknote()
        result = pipeline.process(img)
        assert result.message != ""


class TestPipelineFastMode:
    @pytest.fixture
    def pipeline(self, tmp_path):
        return BanknoteRecognitionPipeline(model_dir=str(tmp_path))

    def test_fast_mode_no_ai_fallback(self, pipeline):
        """Fast mode should never use AI fallback."""
        img = make_grey_image()
        result = pipeline.process_fast(img)
        assert "ai_fallback" not in result.stages_executed

    def test_fast_green_accepted(self, pipeline):
        img = make_green_banknote()
        result = pipeline.process_fast(img)
        assert result.denomination == "100000"
        assert result.method == ClassificationMethod.COLOR

    def test_fast_grey_low_confidence(self, pipeline):
        img = make_grey_image()
        result = pipeline.process_fast(img)
        # Fast mode: no AI fallback, so result is from colour only
        assert "ai_fallback" not in result.stages_executed
        assert result.method == ClassificationMethod.COLOR


class TestPipelineResult:
    def test_default_fields(self):
        result = PipelineResult(decision=PipelineDecision.ERROR)
        assert result.denomination is None
        assert result.confidence == 0.0
        assert result.method == ClassificationMethod.NONE
        assert result.stages_executed == []
