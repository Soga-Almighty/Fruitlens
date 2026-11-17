import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

try:
    from tf_keras.models import load_model
except ImportError:  # TF 2.15 has Keras 2 built in
    from tensorflow.keras.models import load_model
from PIL import Image, ImageOps
import numpy as np
import cv2
import time

# Load model and labels once
model = load_model("models/orange_model/keras_model.h5", compile=False)

with open("models/orange_model/labels.txt", "r") as f:
    class_names = [line.strip() for line in f.readlines()]


def preprocess_image(pil_image):
    """Resize + normalize image exactly as Teachable Machine expects."""
    image = pil_image.convert("RGB")
    image = ImageOps.fit(image, (224, 224), Image.Resampling.LANCZOS)
    img_array = np.asarray(image).astype(np.float32)
    normalized_img = (img_array / 127.5) - 1
    data = np.expand_dims(normalized_img, axis=0)
    return data


def predict(data):
    """Run prediction and return label + confidence."""
    prediction = model.predict(data, verbose=0)
    index = np.argmax(prediction)
    class_name = class_names[index].split(" ", 1)[1]
    confidence = prediction[0][index]
    return class_name, confidence


def predict_from_upload(image_path):
    """Use this when the user uploads an image file."""
    image = Image.open(image_path)
    data = preprocess_image(image)
    return predict(data)


def predict_from_webcam_realtime(predict_every_n_frames=5):
    """
    Continuously analyzes webcam frames in real time.
    predict_every_n_frames controls how often prediction runs
    (running every single frame can be slow/laggy, so we skip some).
    """
    cap = cv2.VideoCapture(0)
    print("Real-time scanning active, Press ESC to stop.")

    frame_count = 0
    label, confidence = "Scanning...", 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Warning: webcam feed not detected!")
            break

        frame_count += 1

        # Only run prediction every N frames to keep things smooth
        if frame_count % predict_every_n_frames == 0:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            data = preprocess_image(pil_image)
            label, confidence = predict(data)

        # Overlay prediction text on the live frame
        display_text = f"{label} ({confidence:.1%})"
        cv2.putText(
            frame, display_text, (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA
        )

        cv2.imshow("Orange Ripeness Scanner - Real-Time", frame)

        key = cv2.waitKey(1)
        if key % 256 == 27:  # ESC to quit
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    mode = input("Choose input mode - 'upload' or 'webcam': ").strip().lower()

    if mode == "upload":
        path = input("Enter image file path: ").strip()
        label, confidence = predict_from_upload(path)
        print(f"Predicted Ripeness: {label}")
        print(f"Confidence: {confidence:.2%}")
    elif mode == "webcam":
        predict_from_webcam_realtime()
    else:
        print("Invalid mode, User-san! Please choose 'upload' or 'webcam'.")