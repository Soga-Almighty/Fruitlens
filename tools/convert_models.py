"""Convert the Teachable Machine models (keras_model.h5) to TensorFlow Lite (model.tflite).

Why: the .tflite file is read by a tiny runtime instead of the whole TensorFlow library, so the server needs
a fraction of the RAM/disk. No quantisation is used, so predictions stay the same as the original model.
Run again whenever you retrain a model:   python tools/convert_models.py
(needs TensorFlow, e.g. your normal local .venv)
"""
import os
import sys
from pathlib import Path

import importlib.util

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
if importlib.util.find_spec("tf_keras"):  # TensorFlow >= 2.16 ships Keras 3; tf_keras keeps the legacy loader
    os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
import numpy as np
import tensorflow as tf

if importlib.util.find_spec("tf_keras"):
    import tf_keras as keras
else:  # TensorFlow 2.15 (see requirements.txt)
    from tensorflow import keras

MODELS = Path(__file__).resolve().parent.parent / "models"
FRUITS = ["banana", "orange", "papaya", "rambutan", "tomato"]


class CompatibleDepthwiseConv2D(keras.layers.DepthwiseConv2D):
    def __init__(self, *args, groups=1, **kwargs):  # old Teachable Machine exports store groups=1
        super().__init__(*args, **kwargs)


def test_inputs(shape, n=40):
    """Random noise, solid colours and gradients, all in the model's input range [-1, 1]."""
    rng = np.random.default_rng(0)
    h, w = shape[1], shape[2]
    batch = [rng.uniform(-1, 1, size=shape[1:]).astype("float32") for _ in range(n // 2)]
    for c in rng.uniform(-1, 1, size=(n // 4, 3)):
        batch.append(np.ones((h, w, 3), "float32") * c.astype("float32"))
    for _ in range(n - len(batch)):
        g = np.linspace(-1, 1, w, dtype="float32")[None, :, None] * np.ones((h, 1, 3), "float32")
        batch.append(g * rng.uniform(0.3, 1))
    return batch


def convert(fruit):
    folder = MODELS / f"{fruit}_model"
    src = folder / "keras_model.h5"
    if not src.exists():
        print(f"{fruit}: {src} not found, skipped")
        return True
    model = keras.models.load_model(str(src), compile=False, custom_objects={"DepthwiseConv2D": CompatibleDepthwiseConv2D})
    data = tf.lite.TFLiteConverter.from_keras_model(model).convert()
    (folder / "model.tflite").write_bytes(data)

    interp = tf.lite.Interpreter(model_content=data)
    interp.allocate_tensors()
    inp, out = interp.get_input_details()[0], interp.get_output_details()[0]
    worst, agree, inputs = 0.0, 0, test_inputs(model.input_shape)
    for x in inputs:
        x = x[None]
        expected = model.predict(x, verbose=0)[0]
        interp.set_tensor(inp["index"], x)
        interp.invoke()
        got = interp.get_tensor(out["index"])[0]
        worst = max(worst, float(np.abs(expected - got).max()))
        agree += int(expected.argmax() == got.argmax())
    ok = worst < 1e-3 and agree == len(inputs)
    print(f"{fruit:9s} {src.stat().st_size/1e6:4.1f} MB h5 -> {len(data)/1e6:4.1f} MB tflite | "
          f"max probability difference {worst:.2e} | same answer on {agree}/{len(inputs)} images | {'OK' if ok else 'MISMATCH'}")
    return ok


if __name__ == "__main__":
    results = [convert(f) for f in (sys.argv[1:] or FRUITS)]
    sys.exit(0 if all(results) else 1)
