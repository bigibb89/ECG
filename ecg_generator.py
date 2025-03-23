import os
import wfdb
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import logging
import traceback

# הגדרות לוג
logging.basicConfig(
    filename='ecg_generator.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# הגדרות נתונים
DATA_DIR = 'data/ptbxl'
OUTPUT_IMG_DIR = 'data/ecg_images'
CSV_PATH = 'data/ptbxl/ptbxl_database.csv'
QUIZ_CSV = 'data/ecg_quiz.csv'
SAMPLING_RATE = 100
NUM_QUESTIONS = 1000

# צור תיקיית תמונות
os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)

# טען מטא-דאטה
try:
    metadata = pd.read_csv(CSV_PATH)
except FileNotFoundError:
    logging.critical(f"קובץ המטא-דאטה לא נמצא: {CSV_PATH}")
    raise

# --------------------------------------------------
# פונקציה ליצירת תמונת אק"ג
# --------------------------------------------------
def save_ecg_plot(record_id):
    try:
        subfolder = f"{int(record_id) // 1000 * 1000:05d}"
        full_path = os.path.join(DATA_DIR, "records100", subfolder, f"{record_id}_lr")
        
        record = wfdb.rdrecord(full_path)
        
        # יצירת הגרף
        fig, axes = plt.subplots(12, 1, figsize=(10, 15))
        colors = plt.cm.viridis(np.linspace(0, 1, 12))
        
        for i, ax in enumerate(axes):
            ax.plot(record.p_signal[:, i], color=colors[i], linewidth=0.8)
            ax.set_title(f'Lead {record.sig_name[i]}', fontsize=8, pad=2)
            ax.axis('off')
        
        img_path = os.path.join(OUTPUT_IMG_DIR, f"{record_id}_lr.png")
        plt.savefig(img_path, bbox_inches='tight', dpi=150)
        plt.close()
        return img_path
        
    except Exception as e:
        logging.error(f"שגיאה ביצירת תמונה ל-{record_id}:\n{traceback.format_exc()}")
        return None

# --------------------------------------------------
# פונקציה ליצירת שאלות
# --------------------------------------------------
def generate_quiz_entry(record):
    try:
        diagnosis = record['diagnosis_superclass']
        same_class = metadata[metadata['diagnosis_superclass'] == diagnosis]
        
        # יצירת מסיחים
        if len(same_class) >= 3:
            distractors = same_class.sample(3)['diagnosis_superclass'].tolist()
        else:
            distractors = same_class['diagnosis_superclass'].tolist()
            distractors += metadata[~metadata.index.isin(same_class.index)].sample(3 - len(distractors))['diagnosis_superclass'].tolist()
        
        options = distractors + [diagnosis]
        np.random.shuffle(options)
        
        img_path = save_ecg_plot(str(record['ecg_id']))
        if not img_path:
            return None
            
        return {
            'ecg_id': record['ecg_id'],
            'image_path': img_path,
            'question': 'מה האבחנה המתאימה לתרשים זה?',
            'options': options,
            'correct_answer': diagnosis
        }
        
    except Exception as e:
        logging.error(f"שגיאה ביצירת שאלה ל-{record['ecg_id']}:\n{traceback.format_exc()}")
        return None

# --------------------------------------------------
# יצירת המאגר
# --------------------------------------------------
quiz_data = []
error_count = 0

try:
    for _, row in tqdm(metadata.sample(NUM_QUESTIONS).iterrows(), total=NUM_QUESTIONS):
        quiz_entry = generate_quiz_entry(row)
        if quiz_entry:
            quiz_data.append(quiz_entry)
        else:
            error_count += 1
            
except Exception as e:
    logging.critical(f"שגיאה כללית:\n{traceback.format_exc()}")
    raise

finally:
    # מניעת יצירת קובץ ריק
    if quiz_data:
        try:
            pd.DataFrame(quiz_data).to_csv(QUIZ_CSV, index=False)
            logging.info(f"נשמרו {len(quiz_data)} שאלות (שגיאות: {error_count})")
        except Exception as e:
            logging.critical(f"שגיאה בשמירת הקובץ:\n{traceback.format_exc()}")
    else:
        logging.critical("לא נוצרו שאלות - קובץ לא נשמר!")
        if os.path.exists(QUIZ_CSV):
            os.remove(QUIZ_CSV)  # מחק קובץ ריק אם נוצר

    print(f"סיום עם {len(quiz_data)} שאלות מוצלחות ו-{error_count} שגיאות")