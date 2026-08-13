import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from utils.improved_model import train_and_evaluate_improved_model


def test_improved_model_outperforms_baseline():
    metrics = train_and_evaluate_improved_model(save=False)
    assert metrics["accuracy"] > 0.5532, metrics


if __name__ == "__main__":
    test_improved_model_outperforms_baseline()
    print("Improved model test passed")
