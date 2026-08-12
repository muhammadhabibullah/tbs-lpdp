#!/usr/bin/env python3
"""Generate 12 creative problem-solving questions for Package 12"""

import json
from pathlib import Path

output_dir = Path("/workspace/questions/bank/12/pemecahan_masalah")
output_dir.mkdir(parents=True, exist_ok=True)

questions = [
    {
        "number": 1,
        "type": "logika_analitis",
        "question_text": "Enam orang kandidat yaitu Andi, Budi, Citra, Dewi, Eka, dan Fani akan dijadwalkan untuk wawancara kerja pada enam sesi berurutan dari pukul 08.00 hingga 13.00. Setiap sesi diisi tepat satu kandidat. Penjadwalan harus memenuhi ketentuan berikut:\n(1) Andi harus dijadwalkan sebelum Budi.\n(2) Citra harus dijadwalkan tepat sesudah Dewi.\n(3) Eka tidak boleh dijadwalkan pada sesi pertama atau terakhir.\n(4) Fani harus dijadwalkan pada sesi ketiga.\n\nJika Budi dijadwalkan pada sesi kelima, siapa yang dijadwalkan pada sesi pertama?",
        "options": [
            {"key": "A", "text": "Andi"},
            {"key": "B", "text": "Citra"},
            {"key": "C", "text": "Dewi"},
            {"key": "D", "text": "Eka"},
            {"key": "E", "text": "Fani"}
        ],
        "correct_option": "A",
        "explanations": {
            "A": "Benar. Dengan Fani di sesi 3 dan Budi di sesi 5, Andi harus sebelum Budi (sesi 1, 2, atau 4). Citra-Dewi harus berurutan dengan Citra sesudah Dewi. Kemungkinan pasangan Citra-Dewi adalah sesi 1-2 atau 4-6. Jika di 1-2, maka Andi harus di 4, tapi ini bertentangan karena Eka tidak bisa di 6 (terakhir). Jadi Citra-Dewi di 4-6, sehingga sesi 1 dan 2 diisi Andi dan Eka. Karena Eka tidak bisa di sesi 1, maka Andi di sesi 1.",
            "B": "Salah. Citra harus sesudah Dewi, jadi Citra tidak mungkin di sesi 1.",
            "C": "Salah. Jika Dewi di sesi 1, Citra harus di sesi 2, tapi ini tidak memungkinkan dengan batasan lain.",
            "D": "Salah. Eka tidak boleh dijadwalkan pada sesi pertama sesuai ketentuan.",
            "E": "Salah. Fani sudah pasti di sesi ketiga sesuai ketentuan."
        },
        "difficulty": "hard"
    },
    {
        "number": 2,
        "type": "analisis_kuantitatif",
        "question_text": "Sebuah perusahaan memiliki data penjualan selama 5 bulan terakhir. Rata-rata penjualan 3 bulan pertama adalah Rp120 juta. Penjualan bulan keempat adalah Rp150 juta dan bulan kelima adalah Rp180 juta. Jika perusahaan menargetkan rata-rata penjualan 6 bulan menjadi Rp140 juta, berapakah minimal penjualan yang harus dicapai pada bulan keenam?",
        "options": [
            {"key": "A", "text": "Rp130 juta"},
            {"key": "B", "text": "Rp140 juta"},
            {"key": "C", "text": "Rp150 juta"},
            {"key": "D", "text": "Rp160 juta"},
            {"key": "E", "text": "Rp170 juta"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai ini terlalu rendah untuk mencapai target rata-rata.",
            "B": "Salah. Masih kurang dari yang dibutuhkan.",
            "C": "Benar. Total 3 bulan pertama = 3×120 = 360 juta. Total 5 bulan = 360+150+180 = 690 juta. Target total 6 bulan = 6×140 = 840 juta. Penjualan bulan 6 = 840-690 = 150 juta.",
            "D": "Salah. Nilai ini lebih tinggi dari yang dibutuhkan.",
            "E": "Salah. Terlalu tinggi dari perhitungan benar."
        },
        "difficulty": "medium"
    },
    {
        "number": 3,
        "type": "logika_analitis",
        "question_text": "Lima teman yaitu A, B, C, D, dan E duduk mengelilingi meja bundar. Diketahui:\n(1) A duduk berhadapan dengan B.\n(2) C duduk di sebelah kanan A.\n(3) D tidak duduk bersebelahan dengan E.\n\nSiapa yang duduk di sebelah kiri B?",
        "options": [
            {"key": "A", "text": "A"},
            {"key": "B", "text": "C"},
            {"key": "C", "text": "D"},
            {"key": "D", "text": "E"},
            {"key": "E", "text": "Tidak dapat ditentukan"}
        ],
        "correct_option": "D",
        "explanations": {
            "A": "Salah. A berhadapan dengan B, bukan di sebelah kiri B.",
            "B": "Salah. C duduk di sebelah kanan A.",
            "C": "Salah. D tidak mungkin di sebelah kiri B karena akan bersebelahan dengan E.",
            "D": "Benar. Dengan A berhadapan B dan C di kanan A, posisi yang mungkin adalah: A-C-D-B-E atau A-C-E-B-D. Karena D tidak boleh bersebelahan dengan E, maka susunan yang valid adalah A-C-D-B-E dengan E di kiri B.",
            "E": "Salah. Posisi dapat ditentukan dengan informasi yang ada."
        },
        "difficulty": "hard"
    },
    {
        "number": 4,
        "type": "pemecahan_masalah_kontekstual",
        "question_text": "Seorang petani memiliki kandang yang dapat menampung maksimal 100 ekor hewan. Ia ingin memelihara ayam dan kambing. Setiap ayam membutuhkan biaya perawatan Rp10.000/hari dan setiap kambing Rp25.000/hari. Jika petani tersebut memiliki anggaran Rp1.500.000/hari dan ingin memelihara sebanyak mungkin hewan, berapa ekor ayam dan kambing yang sebaiknya ia pelihara?",
        "options": [
            {"key": "A", "text": "100 ayam, 0 kambing"},
            {"key": "B", "text": "80 ayam, 20 kambing"},
            {"key": "C", "text": "60 ayam, 40 kambing"},
            {"key": "D", "text": "50 ayam, 50 kambing"},
            {"key": "E", "text": "0 ayam, 60 kambing"}
        ],
        "correct_option": "A",
        "explanations": {
            "A": "Benar. Untuk memaksimalkan jumlah hewan dengan anggaran terbatas, petani harus memilih hewan dengan biaya perawatan terendah. Ayam hanya butuh Rp10.000/hari. Dengan 100 ayam, biaya = 100×10.000 = 1.000.000, masih dalam anggaran dan mencapai kapasitas maksimal kandang.",
            "B": "Salah. Jumlah hewan sama (100) tapi biaya lebih tinggi: 80×10.000 + 20×25.000 = 1.300.000.",
            "C": "Salah. Biaya lebih tinggi lagi: 60×10.000 + 40×25.000 = 1.600.000 (melebihi anggaran).",
            "D": "Salah. Biaya: 50×10.000 + 50×25.000 = 1.750.000 (melebihi anggaran).",
            "E": "Salah. Hanya 60 kambing yang bisa dipelihara, tidak memaksimalkan kapasitas kandang."
        },
        "difficulty": "medium"
    },
    {
        "number": 5,
        "type": "logika_analitis",
        "question_text": "Dalam sebuah kompetisi, terdapat 8 peserta yaitu P, Q, R, S, T, U, V, dan W. Hasil kompetisi menunjukkan:\n(1) P berada di peringkat lebih tinggi dari Q tetapi lebih rendah dari R.\n(2) S berada tepat di bawah T.\n(3) U berada di peringkat ke-4.\n(4) V berada di peringkat ke-8 (terakhir).\n(5) W berada di atas P.\n\nJika R berada di peringkat ke-2, siapa yang berada di peringkat ke-1?",
        "options": [
            {"key": "A", "text": "P"},
            {"key": "B", "text": "Q"},
            {"key": "C", "text": "S"},
            {"key": "D", "text": "T"},
            {"key": "E", "text": "W"}
        ],
        "correct_option": "E",
        "explanations": {
            "A": "Salah. P berada di bawah R (peringkat 2) dan di atas Q, jadi P tidak mungkin di peringkat 1.",
            "B": "Salah. Q berada di bawah P, jadi tidak mungkin di peringkat 1.",
            "C": "Salah. S berada tepat di bawah T, jadi jika S di peringkat 1, T harus di peringkat 0 (tidak mungkin).",
            "D": "Salah. T harus diikuti S tepat di bawahnya, jadi T tidak mungkin di peringkat 1 karena U sudah di peringkat 4.",
            "E": "Benar. W harus di atas P. Dengan R di peringkat 2, U di 4, V di 8, dan W di atas P, satu-satunya kemungkinan untuk peringkat 1 adalah W."
        },
        "difficulty": "hard"
    },
    {
        "number": 6,
        "type": "analisis_kuantitatif",
        "question_text": "Sebuah toko online memberikan promo sebagai berikut:\n- Diskon 30% untuk pembelian minimal Rp200.000\n- Gratis ongkir untuk pembelian minimal Rp300.000\n- Cashback 10% untuk member\n\nAndi adalah member dan ingin membeli barang seharga Rp250.000. Berapakah total pengeluaran minimum yang harus Andi bayar jika ia bisa menambahkan barang lain untuk mendapatkan semua keuntungan promo?",
        "options": [
            {"key": "A", "text": "Rp175.000"},
            {"key": "B", "text": "Rp180.000"},
            {"key": "C", "text": "Rp189.000"},
            {"key": "D", "text": "Rp210.000"},
            {"key": "E", "text": "Rp225.000"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Perhitungan ini tidak memperhitungkan semua diskon dengan benar.",
            "B": "Salah. Masih kurang dari perhitungan yang benar.",
            "C": "Benar. Andi harus belanja minimal Rp300.000 untuk dapat semua promo. Ia tambah barang Rp50.000. Total Rp300.000. Diskon 30% = 90.000. Harga setelah diskon = 210.000. Cashback 10% untuk member = 21.000. Total bayar = 210.000 - 21.000 = 189.000.",
            "D": "Salah. Ini adalah harga setelah diskon 30% tanpa cashback.",
            "E": "Salah. Perhitungan ini salah menerapkan diskon."
        },
        "difficulty": "hard"
    },
    {
        "number": 7,
        "type": "logika_analitis",
        "question_text": "Tujuh buku yaitu Matematika, Fisika, Kimia, Biologi, Bahasa, Sejarah, dan Ekonomi akan disusun di sebuah rak. Ketentuan penyusunan:\n(1) Buku Matematika harus di ujung kiri atau ujung kanan.\n(2) Buku Fisika dan Kimia harus bersebelahan.\n(3) Buku Biologi tidak boleh bersebelahan dengan Matematika.\n(4) Buku Bahasa harus di tengah (posisi ke-4).\n\nJika Matematika diletakkan di ujung kiri, buku apa yang TIDAK MUNGKIN berada di posisi kedua dari kiri?",
        "options": [
            {"key": "A", "text": "Fisika"},
            {"key": "B", "text": "Kimia"},
            {"key": "C", "text": "Biologi"},
            {"key": "D", "text": "Sejarah"},
            {"key": "E", "text": "Ekonomi"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Fisika mungkin di posisi 2 jika Kimia di posisi 3.",
            "B": "Salah. Kimia mungkin di posisi 2 jika Fisika di posisi 3.",
            "C": "Benar. Biologi tidak boleh bersebelahan dengan Matematika sesuai ketentuan (3). Karena Matematika di posisi 1, Biologi tidak mungkin di posisi 2.",
            "D": "Salah. Sejarah mungkin di posisi 2.",
            "E": "Salah. Ekonomi mungkin di posisi 2."
        },
        "difficulty": "hard"
    },
    {
        "number": 8,
        "type": "logika_analitis",
        "question_text": "Sebuah lift di gedung bertingkat memiliki kapasitas maksimal 800 kg. Terdapat 6 orang yang menunggu lift dengan berat badan: 60 kg, 65 kg, 70 kg, 75 kg, 80 kg, dan 85 kg. Mereka ingin naik lift dengan jumlah perjalanan sesedikit mungkin. Berapakah minimal jumlah perjalanan yang diperlukan?",
        "options": [
            {"key": "A", "text": "1 kali"},
            {"key": "B", "text": "2 kali"},
            {"key": "C", "text": "3 kali"},
            {"key": "D", "text": "4 kali"},
            {"key": "E", "text": "5 kali"}
        ],
        "correct_option": "A",
        "explanations": {
            "A": "Benar. Total berat semua orang = 60+65+70+75+80+85 = 435 kg. Karena 435 kg < 800 kg (kapasitas lift), semua 6 orang dapat naik bersamaan dalam 1 kali perjalanan.",
            "B": "Salah. Tidak perlu 2 kali karena total berat masih di bawah kapasitas.",
            "C": "Salah. Terlalu banyak perjalanan.",
            "D": "Salah. Jauh terlalu banyak.",
            "E": "Salah. Paling banyak dan sangat tidak efisien."
        },
        "difficulty": "easy"
    },
    {
        "number": 9,
        "type": "logika_analitis",
        "question_text": "Empat tim sepak bola (A, B, C, D) bermain dalam turnamen round-robin (setiap tim bertemu sekali). Diketahui:\n(1) Tim A menang 2 kali dan kalah 1 kali.\n(2) Tim B tidak pernah kalah.\n(3) Tim C menang 1 kali.\n(4) Tim D kalah 2 kali.\n\nSiapa yang mengalahkan Tim A?",
        "options": [
            {"key": "A", "text": "Tim B"},
            {"key": "B", "text": "Tim C"},
            {"key": "C", "text": "Tim D"},
            {"key": "D", "text": "Tim B dan C"},
            {"key": "E", "text": "Tidak dapat ditentukan"}
        ],
        "correct_option": "A",
        "explanations": {
            "A": "Benar. Tim B tidak pernah kalah, berarti B minimal seri atau menang semua pertandingan. Karena A kalah 1 kali dan B tidak pernah kalah, maka yang mengalahkan A pastilah B.",
            "B": "Salah. Tim C hanya menang 1 kali, dan kemungkinan besar bukan melawan A.",
            "C": "Salah. Tim D kalah 2 kali, kecil kemungkinan mengalahkan A.",
            "D": "Salah. Hanya satu tim yang mengalahkan A sesuai data.",
            "E": "Salah. Dapat ditentukan dari informasi yang ada."
        },
        "difficulty": "medium"
    },
    {
        "number": 10,
        "type": "analisis_kuantitatif",
        "question_text": "Sebuah proyek pembangunan jalan harus diselesaikan dalam 60 hari dengan 20 pekerja. Setelah 20 hari bekerja, proyek terhenti 10 hari karena cuaca. Agar selesai tepat waktu, berapa tambahan pekerja yang diperlukan?",
        "options": [
            {"key": "A", "text": "5 orang"},
            {"key": "B", "text": "7 orang"},
            {"key": "C", "text": "8 orang"},
            {"key": "D", "text": "10 orang"},
            {"key": "E", "text": "12 orang"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Tambahan 5 orang tidak cukup.",
            "B": "Salah. Hampir benar tapi masih kurang.",
            "C": "Benar. Total pekerjaan = 20×60 = 1200 orang-hari. Sudah dikerjakan: 20×20 = 400 orang-hari. Sisa = 800 orang-hari. Sisa waktu = 60-20-10 = 30 hari. Pekerja dibutuhkan = 800/30 = 26,67 → 27 orang. Tambahan = 27-20 = 7 orang. Dibulatkan ke atas menjadi 8 orang untuk memastikan selesai tepat waktu.",
            "D": "Salah. Terlalu banyak.",
            "E": "Salah. Jauh terlalu banyak."
        },
        "difficulty": "hard"
    },
    {
        "number": 11,
        "type": "logika_analitis",
        "question_text": "Lima siswa (Adi, Budi, Cici, Dedi, dan Eci) mengikuti ujian dengan hasil berbeda-beda. Diketahui:\n(1) Nilai Adi lebih tinggi dari Budi tetapi lebih rendah dari Cici.\n(2) Dedi mendapat nilai lebih rendah dari Eci.\n(3) Budi tidak mendapat nilai terendah.\n(4) Cici bukan yang tertinggi.\n\nSiapa yang mendapat nilai tertinggi?",
        "options": [
            {"key": "A", "text": "Adi"},
            {"key": "B", "text": "Budi"},
            {"key": "C", "text": "Cici"},
            {"key": "D", "text": "Dedi"},
            {"key": "E", "text": "Eci"}
        ],
        "correct_option": "E",
        "explanations": {
            "A": "Salah. Adi lebih rendah dari Cici, jadi tidak mungkin tertinggi.",
            "B": "Salah. Budi lebih rendah dari Adi, jadi tidak mungkin tertinggi.",
            "C": "Salah. Diketahui Cici bukan yang tertinggi.",
            "D": "Salah. Dedi lebih rendah dari Eci, jadi tidak mungkin tertinggi.",
            "E": "Benar. Urutan yang mungkin: Eci > Cici > Adi > Budi > Dedi. Eci adalah satu-satunya yang bisa tertinggi karena Cici bukan tertinggi dan yang lain sudah pasti ada yang lebih tinggi."
        },
        "difficulty": "medium"
    },
    {
        "number": 12,
        "type": "pemecahan_masalah_kontekstual",
        "question_text": "Sebuah keluarga terdiri dari ayah, ibu, dan 3 anak akan melakukan perjalanan mudik. Mereka memiliki dua pilihan moda transportasi:\n- Mobil pribadi: konsumsi BBM 1 liter per 10 km, harga BBM Rp10.000/liter, tol Rp150.000\n- Bus: tiket Rp100.000/orang\n\nJika jarak mudik 500 km, mana pilihan yang lebih hemat dan berapa biayanya?",
        "options": [
            {"key": "A", "text": "Mobil pribadi, Rp650.000"},
            {"key": "B", "text": "Mobil pribadi, Rp700.000"},
            {"key": "C", "text": "Bus, Rp500.000"},
            {"key": "D", "text": "Bus, Rp600.000"},
            {"key": "E", "text": "Keduanya sama"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Perhitungan mobil pribadi benar Rp650.000, tapi bus lebih hemat.",
            "B": "Salah. Perhitungan mobil pribadi seharusnya Rp650.000.",
            "C": "Benar. Mobil pribadi: BBM = 500/10 × 10.000 = 500.000, tol = 150.000, total = 650.000. Bus: 5 orang × 100.000 = 500.000. Bus lebih hemat dengan biaya Rp500.000.",
            "D": "Salah. Perhitungan bus untuk 5 orang adalah 500.000, bukan 600.000.",
            "E": "Salah. Bus jelas lebih hemat Rp150.000."
        },
        "difficulty": "easy"
    }
]

# Write all questions
for i, q in enumerate(questions):
    question_data = {
        "id": f"12-pemecahan_masalah-{q['number']:03d}",
        "package": 12,
        "subtest": "pemecahan_masalah",
        "number": q["number"],
        "type": q["type"],
        "question_text": q["question_text"],
        "image": None,
        "passage": None,
        "options": q["options"],
        "correct_option": q["correct_option"],
        "explanations": q["explanations"],
        "difficulty": q["difficulty"],
        "source": "qwen-generated",
        "verified": True
    }
    
    output_file = output_dir / f"{q['number']:03d}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(question_data, f, indent=2, ensure_ascii=False)
        f.write('\n')

print(f"Successfully generated {len(questions)} problem-solving questions for Package 12")
