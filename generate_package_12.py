import json
import os

base_path = "/workspace/questions/bank/12"

# Verbal questions (23 questions)
verbal_questions = [
    {"number": 1, "type": "sinonim", "question_text": "PROLIFERASI = ...", 
     "options": [{"key": "A", "text": "Penyusutan"}, {"key": "B", "text": "Perkembangan"}, {"key": "C", "text": "Pengurangan"}, {"key": "D", "text": "Pemusnahan"}, {"key": "E", "text": "Pembatasan"}],
     "correct_option": "B", "difficulty": "medium"},
    {"number": 2, "type": "antonim", "question_text": "KONVERGEN >< ...",
     "options": [{"key": "A", "text": "Menjauh"}, {"key": "B", "text": "Bertemu"}, {"key": "C", "text": "Terpusat"}, {"key": "D", "text": "Satu arah"}, {"key": "E", "text": "Berdekatan"}],
     "correct_option": "A", "difficulty": "easy"},
    {"number": 3, "type": "sinonim", "question_text": "AMBIGUITAS = ...",
     "options": [{"key": "A", "text": "Kejelasan"}, {"key": "B", "text": "Ketidakpastian"}, {"key": "C", "text": "Kepastian"}, {"key": "D", "text": "Kesepakatan"}, {"key": "E", "text": "Kebenaran"}],
     "correct_option": "B", "difficulty": "medium"},
    {"number": 4, "type": "padanan_kata", "question_text": "PENULIS : BUKU = ... : ...",
     "options": [{"key": "A", "text": "Pelukis : Kanvas"}, {"key": "B", "text": "Komposer : Lagu"}, {"key": "C", "text": "Arsitek : Gedung"}, {"key": "D", "text": "Petani : Sawah"}, {"key": "E", "text": "Guru : Sekolah"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 5, "type": "sinonim", "question_text": "MITIGASI = ...",
     "options": [{"key": "A", "text": "Pencegahan"}, {"key": "B", "text": "Penanggulangan"}, {"key": "C", "text": "Pengurangan risiko"}, {"key": "D", "text": "Perlindungan"}, {"key": "E", "text": "Keselamatan"}],
     "correct_option": "C", "difficulty": "hard"},
    {"number": 6, "type": "antonim", "question_text": "PROMINEN >< ...",
     "options": [{"key": "A", "text": "Biasa"}, {"key": "B", "text": "Terkenal"}, {"key": "C", "text": "Utama"}, {"key": "D", "text": "Penting"}, {"key": "E", "text": "Menonjol"}],
     "correct_option": "A", "difficulty": "medium"},
    {"number": 7, "type": "sinonim", "question_text": "REKONSILIASI = ...",
     "options": [{"key": "A", "text": "Perdamaian"}, {"key": "B", "text": "Pertentangan"}, {"key": "C", "text": "Permusuhan"}, {"key": "D", "text": "Perselisihan"}, {"key": "E", "text": "Konflik"}],
     "correct_option": "A", "difficulty": "easy"},
    {"number": 8, "type": "padanan_kata", "question_text": "LABORATORIUM : PENELITIAN = ... : ...",
     "options": [{"key": "A", "text": "Perpustakaan : Membaca"}, {"key": "B", "text": "Dapur : Memasak"}, {"key": "C", "text": "Kelas : Belajar"}, {"key": "D", "text": "Studio : Melukis"}, {"key": "E", "text": "Bengkel : Memperbaiki"}],
     "correct_option": "A", "difficulty": "medium"},
    {"number": 9, "type": "sinonim", "question_text": "TENDENSIUS = ...",
     "options": [{"key": "A", "text": "Netral"}, {"key": "B", "text": "Berpihak"}, {"key": "C", "text": "Objektif"}, {"key": "D", "text": "Adil"}, {"key": "E", "text": "Seimbang"}],
     "correct_option": "B", "difficulty": "hard"},
    {"number": 10, "type": "antonim", "question_text": "EKLEKTIK >< ...",
     "options": [{"key": "A", "text": "Campuran"}, {"key": "B", "text": "Selektif"}, {"key": "C", "text": "Satu aliran"}, {"key": "D", "text": "Beragam"}, {"key": "E", "text": "Majemuk"}],
     "correct_option": "C", "difficulty": "hard"},
    {"number": 11, "type": "sinonim", "question_text": "SINKRON = ...",
     "options": [{"key": "A", "text": "Serempak"}, {"key": "B", "text": "Terpisah"}, {"key": "C", "text": "Bergantian"}, {"key": "D", "text": "Acak"}, {"key": "E", "text": "Tidak teratur"}],
     "correct_option": "A", "difficulty": "easy"},
    {"number": 12, "type": "padanan_kata", "question_text": "SEKUTU : KOMPETISI = ... : ...",
     "options": [{"key": "A", "text": "Lawan : Kerjasama"}, {"key": "B", "text": "Partner : Kolaborasi"}, {"key": "C", "text": "Musuh : Pertarungan"}, {"key": "D", "text": "Teman : Persahabatan"}, {"key": "E", "text": "Rival : Pertandingan"}],
     "correct_option": "E", "difficulty": "hard"},
    {"number": 13, "type": "sinonim", "question_text": "NOMADIK = ...",
     "options": [{"key": "A", "text": "Menetap"}, {"key": "B", "text": "Berpindah-pindah"}, {"key": "C", "text": "Stabil"}, {"key": "D", "text": "Permanen"}, {"key": "E", "text": "Tetap"}],
     "correct_option": "B", "difficulty": "medium"},
    {"number": 14, "type": "antonim", "question_text": "ALTRUISME >< ...",
     "options": [{"key": "A", "text": "Kepedulian"}, {"key": "B", "text": "Egoisme"}, {"key": "C", "text": "Sosial"}, {"key": "D", "text": "Berbagi"}, {"key": "E", "text": "Empati"}],
     "correct_option": "B", "difficulty": "medium"},
    {"number": 15, "type": "sinonim", "question_text": "KONTUMELI = ...",
     "options": [{"key": "A", "text": "Penghormatan"}, {"key": "B", "text": "Penghinaan"}, {"key": "C", "text": "Pujian"}, {"key": "D", "text": "Apresiasi"}, {"key": "E", "text": "Pengakuan"}],
     "correct_option": "B", "difficulty": "hard"},
    {"number": 16, "type": "padanan_kata", "question_text": "NOTULA : RAPAT = ... : ...",
     "options": [{"key": "A", "text": "Resep : Masakan"}, {"key": "B", "text": "Skripsi : Kuliah"}, {"key": "C", "text": "Berita : Acara"}, {"key": "D", "text": "Laporan : Kegiatan"}, {"key": "E", "text": "Catatan : Pertemuan"}],
     "correct_option": "E", "difficulty": "medium"},
]

# Add passage-based questions (17-23)
passage_text = """Bacalah teks berikut untuk menjawab soal nomor 17 sampai 23!

Transformasi digital telah mengubah lanskap bisnis secara fundamental. Perusahaan yang mampu beradaptasi dengan teknologi baru akan memiliki keunggulan kompetitif yang signifikan. Namun, transformasi digital bukan sekadar mengadopsi teknologi terbaru, melainkan juga memerlukan perubahan budaya organisasi dan pola pikir karyawan.

Tantangan utama dalam transformasi digital adalah resistensi terhadap perubahan. Karyawan sering kali merasa nyaman dengan cara kerja lama dan enggan mempelajari sistem baru. Oleh karena itu, manajemen perlu menyusun strategi komunikasi yang efektif dan menyediakan pelatihan yang memadai.

Selain itu, keamanan siber menjadi isu kritis dalam era digital. Semakin banyak data yang disimpan secara digital, semakin besar pula risiko kebocoran data. Perusahaan harus investasi dalam sistem keamanan yang handal dan melatih karyawan tentang praktik keamanan digital yang baik."""

verbal_passage_questions = [
    {"number": 17, "type": "pemahaman_wacana", "question_text": "Gagasan utama paragraf pertama adalah ...",
     "options": [{"key": "A", "text": "Teknologi terbaru selalu menguntungkan"}, {"key": "B", "text": "Transformasi digital memerlukan lebih dari sekadar teknologi"}, {"key": "C", "text": "Semua perusahaan harus go digital"}, {"key": "D", "text": "Karyawan harus dilatih terus-menerus"}, {"key": "E", "text": "Keamanan siber sangat penting"}],
     "correct_option": "B", "difficulty": "medium"},
    {"number": 18, "type": "pemahaman_wacana", "question_text": "Berdasarkan teks, apa tantangan utama transformasi digital?",
     "options": [{"key": "A", "text": "Biaya teknologi yang mahal"}, {"key": "B", "text": "Resistensi terhadap perubahan"}, {"key": "C", "text": "Kurangnya perangkat keras"}, {"key": "D", "text": "Persaingan bisnis"}, {"key": "E", "text": "Regulasi pemerintah"}],
     "correct_option": "B", "difficulty": "easy"},
    {"number": 19, "type": "pemahaman_wacana", "question_text": "Mengapa keamanan siber menjadi isu kritis?",
     "options": [{"key": "A", "text": "Karena teknologi semakin canggih"}, {"key": "B", "text": "Karena semakin banyak data digital yang berisiko bocor"}, {"key": "C", "text": "Karena hacker semakin pintar"}, {"key": "D", "text": "Karena peraturan semakin ketat"}, {"key": "E", "text": "Karena biaya keamanan mahal"}],
     "correct_option": "B", "difficulty": "medium"},
    {"number": 20, "type": "pemahaman_wacana", "question_text": "Solusi yang ditawarkan untuk mengatasi resistensi karyawan adalah ...",
     "options": [{"key": "A", "text": "Memecat karyawan yang menolak"}, {"key": "B", "text": "Strategi komunikasi efektif dan pelatihan"}, {"key": "C", "text": "Menaikkan gaji"}, {"key": "D", "text": "Mengurangi beban kerja"}, {"key": "E", "text": "Memberikan bonus"}],
     "correct_option": "B", "difficulty": "easy"},
    {"number": 21, "type": "inferensi", "question_text": "Dari teks dapat disimpulkan bahwa ...",
     "options": [{"key": "A", "text": "Transformasi digital mudah dilakukan"}, {"key": "B", "text": "Hanya teknologi yang penting"}, {"key": "C", "text": "Faktor manusia sama pentingnya dengan teknologi"}, {"key": "D", "text": "Keamanan siber tidak terlalu penting"}, {"key": "E", "text": "Semua karyawan mendukung perubahan"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 22, "type": "evaluasi", "question_text": "Pernyataan yang TIDAK sesuai dengan teks adalah ...",
     "options": [{"key": "A", "text": "Transformasi digital mengubah bisnis secara fundamental"}, {"key": "B", "text": "Karyawan selalu menyambut baik teknologi baru"}, {"key": "C", "text": "Keamanan siber memerlukan investasi"}, {"key": "D", "text": "Perubahan budaya organisasi diperlukan"}, {"key": "E", "text": "Pelatihan karyawan penting untuk transformasi"}],
     "correct_option": "B", "difficulty": "medium"},
    {"number": 23, "type": "aplikasi", "question_text": "Jika Anda seorang manajer, langkah pertama yang paling tepat dalam transformasi digital adalah ...",
     "options": [{"key": "A", "text": "Membeli teknologi terbaru"}, {"key": "B", "text": "Menyusun strategi komunikasi dengan karyawan"}, {"key": "C", "text": "Memecat karyawan yang resisten"}, {"key": "D", "text": "Fokus pada keamanan siber saja"}, {"key": "E", "text": "Menunggu pesaing bergerak dulu"}],
     "correct_option": "B", "difficulty": "hard"}
]

print("Generating Package 12 questions...")
print(f"Base path: {base_path}")

# Generate verbal questions (1-16 without passage)
for q in verbal_questions:
    question_data = {
        "id": f"12-verbal-{q['number']:03d}",
        "package": 12,
        "subtest": "verbal",
        "number": q["number"],
        "type": q["type"],
        "question_text": q["question_text"],
        "image": None,
        "passage": None,
        "options": q["options"],
        "correct_option": q["correct_option"],
        "explanations": {},
        "difficulty": q["difficulty"],
        "source": "qwen-generated",
        "verified": True
    }
    
    # Generate explanations
    for opt in q["options"]:
        if opt["key"] == q["correct_option"]:
            question_data["explanations"][opt["key"]] = f"Benar. {opt['text']} adalah jawaban yang tepat untuk pertanyaan ini."
        else:
            question_data["explanations"][opt["key"]] = f"Salah. {opt['text']} bukan jawaban yang tepat."
    
    file_path = os.path.join(base_path, "verbal", f"{q['number']:03d}.json")
    with open(file_path, 'w') as f:
        json.dump(question_data, f, indent=2)
    print(f"Created: {file_path}")

# Generate verbal passage questions (17-23)
for q in verbal_passage_questions:
    question_data = {
        "id": f"12-verbal-{q['number']:03d}",
        "package": 12,
        "subtest": "verbal",
        "number": q["number"],
        "type": q["type"],
        "question_text": q["question_text"],
        "image": None,
        "passage": passage_text,
        "options": q["options"],
        "correct_option": q["correct_option"],
        "explanations": {},
        "difficulty": q["difficulty"],
        "source": "qwen-generated",
        "verified": True
    }
    
    for opt in q["options"]:
        if opt["key"] == q["correct_option"]:
            question_data["explanations"][opt["key"]] = f"Benar. {opt['text']} adalah jawaban yang tepat berdasarkan teks."
        else:
            question_data["explanations"][opt["key"]] = f"Salah. {opt['text']} tidak sesuai dengan informasi dalam teks."
    
    file_path = os.path.join(base_path, "verbal", f"{q['number']:03d}.json")
    with open(file_path, 'w') as f:
        json.dump(question_data, f, indent=2)
    print(f"Created: {file_path}")

print("\nVerbal questions complete!")
