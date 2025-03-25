import os
import wfdb
import pandas as pd
import numpy as np
import logging
from tqdm import tqdm

# הגדרות
DATA_DIR = 'ptbxl'
OUTPUT_IMG_DIR = 'ecg_images'
OUTPUT_CSV = 'ecg_quiz.csv'
SAMPLING_RATE = 100  # 100Hz ב-PTB-XL
NUM_QUESTIONS = 1000  # מספר השאלות ליצירה

# הגדרת לוגים
logging.basicConfig(
    filename='logs/ecg_generator.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("התחלת הרצת הקוד.")

# צור תיקיית תמונות
os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)
logging.info(f"תיקיית התמונות '{OUTPUT_IMG_DIR}' נוצרה או כבר קיימת.")

# --------------------------------------------------
# פונקציה ליצירת תמונת אק"ג
# --------------------------------------------------
def save_ecg_plot(record_id):
    try:
        # טען את הנתונים
        record = wfdb.rdrecord(os.path.join(DATA_DIR, f'records100/{record_id}_hr'))
        logging.info(f"טעינת רשומת אק'ג {record_id} הצליחה.")
        
        # צור את הפלטה
        plt.figure(figsize=(10, 6))
        plt.plot(record.p_signal)
        plt.axis('off')
        
        # שמור כתמונה
        img_path = os.path.join(OUTPUT_IMG_DIR, f"{record_id}.png")
        plt.savefig(img_path, bbox_inches='tight', dpi=150)
        plt.close()
        logging.info(f"תמונת אק'ג נשמרה ב-{img_path}.")
        
        return img_path
    except Exception as e:
        logging.error(f"שגיאה ביצירת תמונת אק'ג עבור {record_id}: {e}")
        return None

# --------------------------------------------------
# פונקציה ליצירת שאלה
# --------------------------------------------------
def generate_quiz_entry(record):
    try:
        # אבחנה ראשית
        diagnosis = record['diagnosis_superclass']
        
        # צור 3 מסיחים מאותה קטגוריה
        same_class = metadata[metadata['diagnosis_superclass'] == diagnosis]
        distractors = same_class.sample(3)['diagnosis_superclass'].unique().tolist()
        
        # השלם ל-3 מסיחים אם חסר
        while len(distractors) < 3:
            distractors.append(metadata.sample(1)['diagnosis_superclass'].values[0])
        
        # ערבב את האפשרויות
        options = distractors + [diagnosis]
        np.random.shuffle(options)
        
        # צור תמונה
        img_path = save_ecg_plot(str(record['ecg_id']))
        
        if img_path is None:
            logging.warning(f"לא ניתן ליצור תמונה עבור {record['ecg_id']}.")
            return None
        
        return {
            'ecg_id': record['ecg_id'],
            'image_path': img_path,
            'question': 'מה האבחנה המתאימה לתרשים זה?',
            'options': options,
            'correct_answer': diagnosis
        }
    except Exception as e:
        logging.error(f"שגיאה ביצירת שאלה עבור {record['ecg_id']}: {e}")
        return None

# --------------------------------------------------
# טען מטא-דאטה
# --------------------------------------------------
try:
    metadata = pd.read_csv(os.path.join(DATA_DIR, 'ptbxl_database.csv'))
    logging.info("מטא-דאטה נטען בהצלחה.")
except Exception as e:
    logging.error(f"שגיאה בטעינת מטא-דאטה: {e}")
    raise

# --------------------------------------------------
# יצירת המאגר
# --------------------------------------------------
quiz_data = []

# עבור על הנתונים עם סרגל התקדמות
for _, row in tqdm(metadata.sample(NUM_QUESTIONS).iterrows(), total=NUM_QUESTIONS):
    quiz_entry = generate_quiz_entry(row)
    if quiz_entry:
        quiz_data.append(quiz_entry)

# שמור ל-CSV
try:
    pd.DataFrame(quiz_data).to_csv(OUTPUT_CSV, index=False)
    logging.info(f"נשמרו {len(quiz_data)} שאלות ב-{OUTPUT_CSV}.")
except Exception as e:
    logging.error(f"שגיאה בשמירת קובץ CSV: {e}")

logging.info("סיום הרצת הקוד.")