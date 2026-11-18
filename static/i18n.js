/* Fruit Lens - language switcher (Indonesian default, English optional).
 *
 * How it works: the pages are written in English. This script translates every piece of text it sees
 * (page text, placeholders, titles, text added later by the app's own JavaScript) using the dictionary
 * below, and remembers the original so switching back to English restores it exactly.
 * Anything that has no entry in the dictionary simply stays in English, so nothing can break.
 *
 * To fix a translation or add a missing one: edit/add a ["English text", "Indonesian text"] pair in PAIRS.
 * To add a new language later: add another dictionary and extend LANGS.
 */
(function () {
  "use strict";

  var KEY = "fl_lang";
  var LANGS = ["id", "en"];
  var lang = "id"; // default for first-time visitors
  try {
    var saved = localStorage.getItem(KEY);
    if (LANGS.indexOf(saved) >= 0) lang = saved;
  } catch (e) {}

  /* ------------------------------------------------------------------ */
  /* Dictionary: exact English text -> Indonesian                       */
  /* ------------------------------------------------------------------ */
  var PAIRS = [
    // ---- brand / navigation
    ["Ripeness Scanner", "Pemindai Kematangan"],
    ["Computer Vision Fruit Scanner", "Pemindai Buah Computer Vision"],
    ["Dashboard", "Dasbor"],
    ["Scan Fruit", "Pindai Buah"],
    ["Fruit Library", "Pustaka Buah"],
    ["Analysis History", "Riwayat Analisis"],
    ["Recommendations", "Rekomendasi"],
    ["About Platform", "Tentang Platform"],
    ["Home", "Beranda"],
    ["Scan", "Pindai"],
    ["Library", "Pustaka"],
    ["History", "Riwayat"],
    ["Tips", "Tips"],
    ["Account", "Akun"],
    ["Language", "Bahasa"],
    ["Sign out", "Keluar"],
    ["Install app", "Pasang aplikasi"],
    ["Loading...", "Memuat..."],
    ["Checking server...", "Memeriksa server..."],
    ["Server online", "Server aktif"],
    ["Server offline", "Server tidak terhubung"],
    ["Account menu", "Menu akun"],
    ["Search fruit guides...", "Cari panduan buah..."],
    ["Search fruit guides", "Cari panduan buah"],
    ["Fruit Lens - Smart Vision for Fresher Choices", "Fruit Lens - Penglihatan Cerdas untuk Pilihan Lebih Segar"],
    ["Sign in - Fruit Lens", "Masuk - Fruit Lens"],

    // ---- dashboard
    ["Dashboard Overview", "Ringkasan Dasbor"],
    ["Quick Scan", "Pindai Cepat"],
    ["Computer Vision Active", "Computer Vision Aktif"],
    ["Hello", "Halo"],
    ["! Ready to check your fruits?", "! Siap memeriksa buah Anda?"],
    ["Upload or snap a photo of Papayas, Tomatoes, Oranges, Bananas, or Rambutans for real-time freshness & shelf-life prediction.",
      "Unggah atau ambil foto Pepaya, Tomat, Jeruk, Pisang, atau Rambutan untuk prediksi kesegaran dan masa simpan secara langsung."],
    ["Scan a Fruit Now", "Pindai Buah Sekarang"],
    ["Total Scanned", "Total Dipindai"],
    ["Fresh / Ripe", "Segar / Matang"],
    ["Consume or compost", "Konsumsi atau kompos"],
    ["Condition Distribution", "Distribusi Kondisi"],
    ["Across all saved scans", "Dari semua pindaian tersimpan"],
    ["Scans", "Pindaian"],
    ["Recent Scans", "Pindaian Terbaru"],
    ["Latest classifications from your camera and uploads", "Klasifikasi terbaru dari kamera dan unggahan Anda"],
    ["View All", "Lihat Semua"],
    ["View all", "Lihat semua"],
    ["Supported Fruit Models", "Model Buah yang Didukung"],
    ["View Full Library →", "Lihat Pustaka Lengkap →"],
    ["No scans yet", "Belum ada pindaian"],
    ["Your classifications will appear here.", "Hasil klasifikasi Anda akan muncul di sini."],

    // ---- conditions / stages
    ["Unripe", "Belum Matang"],
    ["Ripe", "Matang"],
    ["Rotten", "Busuk"],
    ["Overripe", "Terlalu Matang"],
    ["Spoiled", "Rusak"],

    // ---- scan page
    ["Ready to scan", "Siap memindai"],
    ["Reset", "Atur Ulang"],
    ["Position fruit within center target", "Posisikan buah di dalam target tengah"],
    ["Select the fruit type before scanning.", "Pilih jenis buah sebelum memindai."],
    ["Analyzing your fruit...", "Menganalisis buah Anda..."],
    ["Running the ripeness model", "Menjalankan model kematangan"],
    ["Select Fruit", "Pilih Buah"],
    ["-- Choose a fruit --", "-- Pilih buah --"],
    ["Upload Image", "Unggah Gambar"],
    ["Open Camera", "Buka Kamera"],
    ["Take Photo", "Ambil Foto"],
    ["Capture & Analyze", "Ambil & Analisis"],
    ["Scan Guidelines", "Panduan Memindai"],
    ["Pick the right fruit first", "Pilih buah yang tepat terlebih dahulu"],
    ["Each fruit has its own model, so choosing the wrong type gives a wrong answer.",
      "Setiap buah punya modelnya sendiri, sehingga memilih jenis yang salah akan memberi hasil yang salah."],
    ["Centre a single fruit", "Tempatkan satu buah di tengah"],
    ["The photo is centre-cropped to a square, so keep the fruit in the middle.",
      "Foto dipotong menjadi persegi dari bagian tengah, jadi letakkan buah di tengah."],
    ["Good light, plain background", "Cahaya baik, latar polos"],
    ["Avoid harsh shadows. A neutral surface helps the model focus on the fruit.",
      "Hindari bayangan keras. Permukaan netral membantu model fokus pada buah."],
    ["Your latest scans", "Pindaian terbaru Anda"],
    ["Camera live", "Kamera aktif"],
    ["Image loaded", "Gambar dimuat"],
    ["Photo captured", "Foto diambil"],
    ["Fruit Preview", "Pratinjau Buah"],
    ["Detected Fruit", "Buah Terdeteksi"],

    // ---- result page
    ["AI Classification Result", "Hasil Klasifikasi AI"],
    ["Classification Confidence:", "Tingkat Keyakinan Klasifikasi:"],
    ["Scan Another", "Pindai Lagi"],
    ["Fruit Guide", "Panduan Buah"],
    ["Delete this record", "Hapus catatan ini"],
    ["The model is not very sure about this photo. Retake it in better light with a plain background, and make sure the selected fruit matches the photo.",
      "Model kurang yakin dengan foto ini. Ambil ulang dengan cahaya yang lebih baik dan latar polos, dan pastikan buah yang dipilih sesuai dengan foto."],
    ["Freshness Index", "Indeks Kesegaran"],
    ["Optimal Peak Freshness", "Kesegaran Puncak Optimal"],
    ["Optimal peak freshness", "Kesegaran puncak optimal"],
    ["Ripening Time", "Waktu Pematangan"],
    ["Estimated Shelf Life", "Perkiraan Masa Simpan"],
    ["Before quality degradation begins", "Sebelum kualitas mulai menurun"],
    ["Recommended Temp", "Suhu yang Disarankan"],
    ["Ripening Lifecycle Stage", "Tahap Siklus Pematangan"],
    ["Model Probabilities", "Probabilitas Model"],
    ["The freshness index weights these probabilities by condition, so uncertain photos score between stages.",
      "Indeks kesegaran membobot probabilitas ini berdasarkan kondisi, sehingga foto yang kurang jelas mendapat skor di antara dua tahap."],
    ["Storage Protocol", "Protokol Penyimpanan"],
    ["Consumption Window", "Waktu Konsumsi"],
    ["Culinary Suggestion", "Saran Kuliner"],
    ["Keep away from ethylene-sensitive crops. Wrap stems in foil to slow down gas release.",
      "Jauhkan dari hasil panen yang peka terhadap etilen. Bungkus tangkai dengan aluminium foil untuk memperlambat pelepasan gas."],
    ["Best eaten raw within the next 48 hours for maximum Vitamin B6 & C absorption.",
      "Paling baik dimakan mentah dalam 48 jam ke depan untuk penyerapan Vitamin B6 & C maksimal."],
    ["Ideal for breakfast oatmeal, fresh smoothies, or baking banana bread if spots appear.",
      "Ideal untuk oatmeal sarapan, smoothie segar, atau dipanggang menjadi bolu pisang jika mulai berbintik."],
    ["Already at peak ripeness", "Sudah di puncak kematangan"],
    ["Estimated time until ripe", "Perkiraan waktu hingga matang"],
    ["Past the edible stage", "Sudah melewati tahap layak makan"],
    ["Banana (Cavendish)", "Pisang (Cavendish)"],
    ["Cool, dry pantry counter", "Meja dapur yang sejuk dan kering"],

    // ---- library / guide
    ["Fruit Database & Guides", "Basis Data & Panduan Buah"],
    ["Fruit Species Database", "Basis Data Spesies Buah"],
    ["Open a fruit to see its ripeness stages and storage advice", "Buka satu buah untuk melihat tahap kematangan dan saran penyimpanannya"],
    ["All", "Semua"],
    ["Ripening:", "Pematangan:"],
    ["View Guide →", "Lihat Panduan →"],
    ["Back to library", "Kembali ke pustaka"],
    ["Ripening", "Pematangan"],
    ["Storage temp", "Suhu simpan"],
    ["Best place", "Tempat terbaik"],
    ["Ethylene", "Etilen"],
    ["Ripeness stages", "Tahap kematangan"],
    ["Ripens in", "Matang dalam"],
    ["Shelf life", "Daya simpan"],
    ["Storage", "Penyimpanan"],
    ["Eating", "Konsumsi"],
    ["Cooking", "Memasak"],
    ["Scan a fruit", "Pindai buah"],

    // ---- history
    ["Computer Vision Log", "Log Computer Vision"],
    ["Analysis Logs", "Log Analisis"],
    ["Every scan is saved automatically to your account", "Setiap pindaian disimpan otomatis ke akun Anda"],
    ["All fruits", "Semua buah"],
    ["All conditions", "Semua kondisi"],
    ["Export CSV", "Ekspor CSV"],
    ["Photo", "Foto"],
    ["Timestamp", "Waktu"],
    ["Fruit", "Buah"],
    ["Condition", "Kondisi"],
    ["Confidence", "Keyakinan"],
    ["· Freshness", "· Kesegaran"],
    ["Freshness", "Kesegaran"],
    ["Action", "Aksi"],
    ["View", "Lihat"],
    ["Delete", "Hapus"],
    ["Delete scan", "Hapus pindaian"],
    ["No scans found. Scan a fruit and it will be saved here automatically.",
      "Tidak ada pindaian. Pindai buah dan hasilnya akan tersimpan di sini secara otomatis."],

    // ---- recommendations / tips
    ["Smart Storage Recommendations", "Rekomendasi Penyimpanan Cerdas"],
    ["Smart Storage & Waste Reduction", "Penyimpanan Cerdas & Pengurangan Limbah"],
    ["Built from your latest scan of each fruit (last 14 days), plus general storage tips",
      "Disusun dari pindaian terbaru setiap buah (14 hari terakhir), ditambah tips penyimpanan umum"],
    ["For your fruits", "Untuk buah Anda"],
    ["General tips", "Tips umum"],
    ["No personalised advice yet", "Belum ada saran personal"],
    ["Scan a fruit and tailored storage advice will show up here.",
      "Pindai buah dan saran penyimpanan yang sesuai akan muncul di sini."],
    ["Act Now", "Segera Tindak"],
    ["Eat Soon", "Segera Dimakan"],
    ["Wait", "Tunggu"],
    ["High Priority", "Prioritas Tinggi"],
    ["Pro Tip", "Tips Ahli"],
    ["Habit", "Kebiasaan"],
    ["Ethylene Gas Separation", "Pisahkan Gas Etilen"],
    ["Bananas, tomatoes and papayas release ethylene, which speeds up ripening of nearby produce. Store them apart from fruit you want to keep longer, such as oranges.",
      "Pisang, tomat, dan pepaya melepaskan etilen yang mempercepat pematangan produk di dekatnya. Simpan terpisah dari buah yang ingin Anda awetkan lebih lama, seperti jeruk."],
    ["Refrigeration Timing", "Waktu Menyimpan di Kulkas"],
    ["Do not refrigerate tomatoes or papayas while they are still green: chilling interrupts ripening. Once ripe, the fridge helps papaya and rambutan last longer.",
      "Jangan masukkan tomat atau pepaya ke kulkas selagi masih hijau: dingin menghentikan pematangan. Setelah matang, kulkas membantu pepaya dan rambutan bertahan lebih lama."],
    ["Check Fruit Daily", "Periksa Buah Setiap Hari"],
    ["Inspect stored fruit every day. One rotting fruit can spread mould to the rest of the bowl.",
      "Periksa buah simpanan setiap hari. Satu buah yang membusuk dapat menyebarkan jamur ke seluruh isi wadah."],
    ["Wash Just Before Eating", "Cuci Sesaat Sebelum Dimakan"],
    ["Moisture speeds up mould growth. Keep fruit dry in storage and rinse it right before eating.",
      "Kelembapan mempercepat pertumbuhan jamur. Simpan buah dalam keadaan kering dan bilas tepat sebelum dimakan."],

    // ---- about
    ["About Fruit Lens AI Platform", "Tentang Platform Fruit Lens AI"],
    ["About Fruit Lens AI", "Tentang Fruit Lens AI"],
    ["Fruit Lens is a Computer Vision research prototype developed using Google Teachable Machine image classification algorithms. Designed for agricultural technology education and food waste reduction.",
      "Fruit Lens adalah prototipe penelitian Computer Vision yang dikembangkan menggunakan algoritma klasifikasi gambar Google Teachable Machine. Dirancang untuk edukasi teknologi pertanian dan pengurangan limbah makanan."],
    ["Smart Detection", "Deteksi Cerdas"],
    ["Convolutional neural networks trained with Teachable Machine on your own fruit photo dataset, one model per fruit.",
      "Jaringan saraf konvolusional yang dilatih dengan Teachable Machine pada dataset foto buah Anda sendiri, satu model per buah."],
    ["Better Storage", "Penyimpanan Lebih Baik"],
    ["Actionable advice on humidity, temperature, and atmospheric separation.",
      "Saran praktis tentang kelembapan, suhu, dan pemisahan atmosfer penyimpanan."],
    ["Less Food Waste", "Lebih Sedikit Sampah Makanan"],
    ["Extends pantry usage lifecycle and supports compost redirection.",
      "Memperpanjang masa pakai bahan di dapur dan mendukung pengalihan ke kompos."],

    // ---- fruit names, categories
    ["Banana", "Pisang"], ["Tomato", "Tomat"], ["Papaya", "Pepaya"], ["Orange", "Jeruk"], ["Rambutan", "Rambutan"],
    ["Tropical", "Tropis"], ["Fruit vegetable", "Sayuran buah"], ["Citrus", "Sitrus"],

    // ---- fruit guide content (built-in data)
    ["High-potassium climacteric fruit. The peel shifts from green to yellow, then brown-spotted as starch turns to sugar.",
      "Buah klimakterik kaya kalium. Kulitnya berubah dari hijau menjadi kuning, lalu berbintik cokelat saat pati berubah menjadi gula."],
    ["Rich in lycopene. Colour moves from green to deep red while the flesh softens; cold storage dulls flavour.",
      "Kaya likopen. Warna berubah dari hijau menjadi merah tua saat daging buah melunak; penyimpanan dingin membuat rasanya hambar."],
    ["Tropical fruit with papain enzyme. Skin turns from green to yellow-orange and the flesh softens as it ripens.",
      "Buah tropis dengan enzim papain. Kulit berubah dari hijau menjadi kuning-oranye dan daging buah melunak saat matang."],
    ["Hairy-shelled fruit that does not ripen after harvest. Spines turn from yellow-green to red; the skin browns fast.",
      "Buah berkulit berambut yang tidak matang setelah dipanen. Rambutnya berubah dari kuning-hijau menjadi merah; kulitnya cepat menjadi cokelat."],
    ["Citrus rich in Vitamin C. Non-climacteric, so it will not sweeten after picking; a firm rind with even colour is best.",
      "Jeruk kaya Vitamin C. Bersifat non-klimakterik sehingga tidak bertambah manis setelah dipetik; kulit yang kencang dan berwarna merata paling baik."],
    ["Does not ripen after harvest", "Tidak matang setelah panen"],
    ["Cool room, away from direct sun", "Ruangan sejuk, jauh dari sinar matahari langsung"],
    ["Counter, stem-side down", "Di meja dapur, sisi tangkai menghadap ke bawah"],
    ["20°C - 24°C (10°C - 13°C once ripe)", "20°C - 24°C (10°C - 13°C setelah matang)"],
    ["Room temperature, fridge once ripe", "Suhu ruang, kulkas setelah matang"],
    ["Fridge, perforated bag", "Kulkas, dalam kantong berlubang"],
    ["Cool ventilated area or fridge crisper", "Tempat sejuk berventilasi atau laci sayur kulkas"],
    ["High ethylene producer", "Penghasil etilen tinggi"],
    ["Moderate ethylene producer", "Penghasil etilen sedang"],
    ["Low ethylene producer", "Penghasil etilen rendah"],
    ["Very low ethylene producer", "Penghasil etilen sangat rendah"],

    ["Green & starchy", "Hijau & bertepung"],
    ["Green & firm", "Hijau & keras"],
    ["Maturing phase", "Fase pematangan"],
    ["Immature (yellow-green)", "Belum matang (kuning-hijau)"],
    ["Immature rind", "Kulit belum matang"],
    ["Peak firm ripeness", "Matang puncak, masih padat"],
    ["Peak freshness", "Kesegaran puncak"],
    ["Decomposed surface", "Permukaan membusuk"],
    ["Won't ripen further", "Tidak akan matang lagi"],
    ["Expired", "Kedaluwarsa"],

    ["Keep at room temperature. A paper bag or a ripe fruit nearby speeds ripening.",
      "Simpan pada suhu ruang. Kantong kertas atau buah matang di dekatnya mempercepat pematangan."],
    ["Wait until yellow with a few spots; green bananas are starchy.",
      "Tunggu hingga kuning dengan sedikit bintik; pisang hijau masih bertepung."],
    ["Green bananas can be boiled or fried as a savoury side or chips.",
      "Pisang hijau bisa direbus atau digoreng sebagai lauk gurih atau keripik."],
    ["Keep away from other ethylene-sensitive produce. Wrap the crown in foil to slow ripening.",
      "Jauhkan dari hasil panen lain yang peka terhadap etilen. Bungkus bagian tangkai dengan aluminium foil untuk memperlambat pematangan."],
    ["Best eaten within 2-3 days for the ideal sugar and texture balance.",
      "Paling baik dimakan dalam 2-3 hari untuk keseimbangan rasa manis dan tekstur yang ideal."],
    ["Great for snacking, smoothies, oatmeal or fried banana.",
      "Cocok untuk camilan, smoothie, oatmeal, atau pisang goreng."],
    ["Ripen at room temperature out of direct sun. Do not refrigerate: cold blocks ripening.",
      "Matangkan pada suhu ruang, jauh dari sinar matahari langsung. Jangan masukkan ke kulkas: dingin menghambat pematangan."],
    ["Wait until fully red and slightly soft for the best flavour.",
      "Tunggu hingga merah penuh dan sedikit lunak untuk rasa terbaik."],
    ["Green tomatoes can be fried, pickled or made into green sambal.",
      "Tomat hijau bisa digoreng, diasinkan, atau dibuat sambal hijau."],
    ["Store stem-side down on the counter. Chill only to extend life, then warm up before eating.",
      "Simpan dengan sisi tangkai menghadap ke bawah di meja dapur. Dinginkan hanya untuk memperpanjang umur, lalu biarkan hangat sebelum dimakan."],
    ["Eat within 3-4 days, raw for the best flavour.",
      "Makan dalam 3-4 hari, sebaiknya mentah untuk rasa terbaik."],
    ["Ideal for salads, sandwiches, fresh sauces and sambal.",
      "Ideal untuk salad, sandwich, saus segar, dan sambal."],
    ["Keep at room temperature until about 70% of the skin is yellow. Avoid the fridge while green.",
      "Simpan pada suhu ruang hingga sekitar 70% kulit berwarna kuning. Hindari kulkas selama masih hijau."],
    ["Wait for yellow-orange skin and a slight give before cutting for sweet flesh.",
      "Tunggu hingga kulit kuning-oranye dan sedikit lunak sebelum dipotong agar dagingnya manis."],
    ["Green papaya works in savoury dishes such as urap, vegetable soup or som tum.",
      "Pepaya hijau cocok untuk masakan gurih seperti urap, sayur bening, atau som tum."],
    ["Move to the fridge to slow ripening and keep the flesh firm.",
      "Pindahkan ke kulkas untuk memperlambat pematangan dan menjaga daging buah tetap padat."],
    ["Eat within 2-3 days; ripe papaya bruises easily.",
      "Makan dalam 2-3 hari; pepaya matang mudah memar."],
    ["Fresh slices, fruit salad, smoothies or iced fruit desserts.",
      "Irisan segar, salad buah, smoothie, atau es buah."],
    ["Rambutan does not ripen after picking. Keep cool in a perforated bag.",
      "Rambutan tidak matang setelah dipetik. Simpan di tempat sejuk dalam kantong berlubang."],
    ["Likely sour or astringent; choose fully red fruit when possible.",
      "Kemungkinan asam atau sepat; pilih buah yang merah penuh bila memungkinkan."],
    ["Add to fruit salad or syrup to balance the sourness.",
      "Tambahkan ke salad buah atau sirup untuk menyeimbangkan rasa asam."],
    ["Refrigerate in a perforated bag; the skin browns quickly at room temperature.",
      "Simpan di kulkas dalam kantong berlubang; kulitnya cepat menjadi cokelat pada suhu ruang."],
    ["Eat within 2-3 days while the flesh is at its sweetest.",
      "Makan dalam 2-3 hari selagi daging buahnya paling manis."],
    ["Eat fresh, serve chilled, or add to mixed fruit desserts.",
      "Makan langsung, sajikan dingin, atau tambahkan ke hidangan penutup buah campur."],
    ["Oranges do not ripen after picking. Keep in a cool, ventilated place.",
      "Jeruk tidak matang setelah dipetik. Simpan di tempat sejuk dan berventilasi."],
    ["May taste sour. Rind colour alone is not a reliable maturity sign for every variety.",
      "Bisa terasa asam. Warna kulit saja bukan tanda kematangan yang dapat diandalkan untuk setiap varietas."],
    ["Juice with a little honey, or use zest and slices in marinades.",
      "Peras dengan sedikit madu, atau gunakan parutan kulit dan irisannya untuk marinasi."],
    ["Keep in a cool ventilated place or the fridge crisper. Keep dry to avoid mould.",
      "Simpan di tempat sejuk berventilasi atau laci sayur kulkas. Jaga tetap kering agar tidak berjamur."],
    ["Eat or juice within 1-2 weeks for the best juiciness and Vitamin C.",
      "Makan atau peras dalam 1-2 minggu untuk kesegaran dan Vitamin C terbaik."],
    ["Fresh segments, juice, dressings, or zest in baking.",
      "Siung segar, jus, dressing, atau parutan kulit untuk membuat kue."],
    ["Isolate immediately so mould spores do not spread to nearby fruit.",
      "Pisahkan segera agar spora jamur tidak menyebar ke buah di dekatnya."],
    ["Do not eat. Discard if you see mould, slime, leaking juice or a fermented smell.",
      "Jangan dimakan. Buang jika terlihat jamur, lendir, air buah merembes, atau berbau fermentasi."],
    ["Not suitable for cooking. Send to compost or organic waste.",
      "Tidak layak dimasak. Jadikan kompos atau buang ke sampah organik."],

    // ---- toasts, statuses, messages (app + server)
    ["Record deleted", "Catatan dihapus"],
    ["No data", "Tidak ada data"],
    ["Delete this scan record?", "Hapus catatan pindaian ini?"],
    ["Failed to load data", "Gagal memuat data"],
    ["Please choose a fruit type first.", "Pilih jenis buah terlebih dahulu."],
    ["Please upload an image or take a photo first.", "Unggah gambar atau ambil foto terlebih dahulu."],
    ["The camera is not ready yet.", "Kamera belum siap."],
    ["The live camera is not available here. Use Upload Image instead.", "Kamera langsung tidak tersedia di sini. Gunakan Unggah Gambar."],
    ["Fruit Lens installed!", "Fruit Lens berhasil dipasang!"],
    ["Tap the Share button, then 'Add to Home Screen'.", "Ketuk tombol Bagikan, lalu pilih 'Tambah ke Layar Utama'."],
    ["Open your browser menu and choose 'Install app' / 'Add to Home screen'.", "Buka menu browser Anda dan pilih 'Pasang aplikasi' / 'Tambahkan ke layar utama'."],
    ["No internet connection. Check your signal and try again.", "Tidak ada koneksi internet. Periksa sinyal Anda dan coba lagi."],
    ["Your session has expired. Please sign in again.", "Sesi Anda telah berakhir. Silakan masuk lagi."],
    ["That photo is too large (maximum 12 MB). Try again or choose a smaller photo.", "Foto itu terlalu besar (maksimal 12 MB). Coba lagi atau pilih foto yang lebih kecil."],
    ["No image selected.", "Tidak ada gambar yang dipilih."],
    ["Please choose a valid fruit type.", "Pilih jenis buah yang valid."],
    ["That file is not a valid image.", "File itu bukan gambar yang valid."],
    ["Fruit not found.", "Buah tidak ditemukan."],
    ["Scan not found.", "Pindaian tidak ditemukan."],
    ["Could not read that image.", "Gambar itu tidak dapat dibaca."],

    // ---- login page
    ["Computer Vision Ripeness Scanner", "Pemindai Kematangan Computer Vision"],
    ["Know when your fruit is at its best.", "Ketahui kapan buah Anda berada di kondisi terbaiknya."],
    ["Scan bananas, tomatoes, papayas, oranges and rambutans. Get ripeness, shelf life and storage advice in seconds.",
      "Pindai pisang, tomat, pepaya, jeruk, dan rambutan. Dapatkan tingkat kematangan, masa simpan, dan saran penyimpanan dalam hitungan detik."],
    ["Instant ripeness scan", "Pindai kematangan instan"],
    ["Upload a photo or use your camera.", "Unggah foto atau gunakan kamera Anda."],
    ["Your own scan history", "Riwayat pindaian milik Anda"],
    ["Saved to your account, private to you.", "Tersimpan di akun Anda, hanya Anda yang dapat melihat."],
    ["Smart storage tips", "Tips penyimpanan cerdas"],
    ["Personal advice to cut food waste.", "Saran personal untuk mengurangi sampah makanan."],
    ["5 fruit models", "5 model buah"],
    ["3 ripeness stages each", "Masing-masing 3 tahap kematangan"],
    ["Sign in", "Masuk"],
    ["Create account", "Buat akun"],
    ["Welcome back", "Selamat datang kembali"],
    ["Sign in to see your scans and keep checking your fruit.", "Masuk untuk melihat pindaian Anda dan terus memeriksa buah Anda."],
    ["Continue with Google", "Lanjutkan dengan Google"],
    ["Redirecting to Google...", "Mengalihkan ke Google..."],
    ["or with email", "atau dengan email"],
    ["Full name", "Nama lengkap"],
    ["Email", "Email"],
    ["6-digit code", "Kode 6 digit"],
    ["Password", "Kata sandi"],
    ["New password", "Kata sandi baru"],
    ["Keep me signed in", "Tetap masuk"],
    ["Forgot password?", "Lupa kata sandi?"],
    ["Back to sign in", "Kembali ke halaman masuk"],
    ["Resend code", "Kirim ulang kode"],
    ["Accounts are secured by InsForge. Your scans are private to your account.",
      "Akun diamankan oleh InsForge. Pindaian Anda bersifat pribadi untuk akun Anda."],
    ["Your name", "Nama Anda"],
    ["Your password", "Kata sandi Anda"],
    ["Show password", "Tampilkan kata sandi"],
    ["Hide password", "Sembunyikan kata sandi"],
    ["Create your account", "Buat akun Anda"],
    ["We'll email you a code to confirm it's really you.", "Kami akan mengirim kode ke email Anda untuk memastikan ini benar-benar Anda."],
    ["It takes a few seconds. Your scan history stays with your account.", "Hanya butuh beberapa detik. Riwayat pindaian Anda tetap tersimpan di akun Anda."],
    ["Reset your password", "Atur ulang kata sandi"],
    ["Enter your email and we'll send you a reset code.", "Masukkan email Anda dan kami akan mengirim kode pengaturan ulang."],
    ["Enter your email and we'll send you a reset link.", "Masukkan email Anda dan kami akan mengirim tautan pengaturan ulang."],
    ["Send reset code", "Kirim kode reset"],
    ["Send reset link", "Kirim tautan reset"],
    ["Choose a new password", "Pilih kata sandi baru"],
    ["Enter the 6-digit code we emailed you and choose a new password.", "Masukkan kode 6 digit yang kami kirim lewat email dan pilih kata sandi baru."],
    ["Enter your new password.", "Masukkan kata sandi baru Anda."],
    ["Update password", "Perbarui kata sandi"],
    ["Check your email", "Periksa email Anda"],
    ["Enter the 6-digit code we sent you. It expires in a few minutes.", "Masukkan kode 6 digit yang kami kirim. Kode kedaluwarsa dalam beberapa menit."],
    ["We sent you a verification link. Click it, then come back and sign in.", "Kami mengirim tautan verifikasi. Klik tautan itu, lalu kembali dan masuk."],
    ["Verify email", "Verifikasi email"],
    ["I verified, sign in", "Sudah verifikasi, masuk"],
    ["Weak", "Lemah"], ["Fair", "Cukup"], ["Good", "Baik"], ["Strong", "Kuat"],
    ["Name must be at least 2 characters.", "Nama minimal 2 karakter."],
    ["Name must be 2-60 characters.", "Nama harus 2-60 karakter."],
    ["Please enter a valid email address.", "Masukkan alamat email yang valid."],
    ["Please enter your password.", "Masukkan kata sandi Anda."],
    ["Please enter a password (max. 128 characters).", "Masukkan kata sandi (maksimal 128 karakter)."],
    ["Please enter a new password.", "Masukkan kata sandi baru."],
    ["Please enter your email and password.", "Masukkan email dan kata sandi Anda."],
    ["Enter the 6-digit code from your email.", "Masukkan kode 6 digit dari email Anda."],
    ["That code is invalid or has expired.", "Kode itu tidak valid atau sudah kedaluwarsa."],
    ["Please verify your email first.", "Verifikasi email Anda terlebih dahulu."],
    ["Please verify your email first. Use \"Resend code\" if you need a new one.", "Verifikasi email Anda terlebih dahulu. Gunakan \"Kirim ulang kode\" jika perlu kode baru."],
    ["A new verification link is on its way.", "Tautan verifikasi baru sedang dikirim."],
    ["A new code is on its way. Check your inbox (and spam folder).", "Kode baru sedang dikirim. Periksa kotak masuk (dan folder spam) Anda."],
    ["If that email has an account, a reset link is on its way. Click it to choose a new password.", "Jika email itu terdaftar, tautan reset sedang dikirim. Klik tautan itu untuk memilih kata sandi baru."],
    ["If that email has an account, a 6-digit code is on its way.", "Jika email itu terdaftar, kode 6 digit sedang dikirim."],
    ["Password updated. You can sign in now.", "Kata sandi diperbarui. Sekarang Anda dapat masuk."],
    ["Email verified. Please sign in.", "Email terverifikasi. Silakan masuk."],
    ["That link is invalid or has expired. Please request a new one.", "Tautan itu tidak valid atau sudah kedaluwarsa. Silakan minta yang baru."],
    ["This reset link is invalid or has expired. Please request a new one.", "Tautan reset ini tidak valid atau sudah kedaluwarsa. Silakan minta yang baru."],
    ["Something went wrong. Please try again.", "Terjadi kesalahan. Silakan coba lagi."],
    ["Incorrect email or password.", "Email atau kata sandi salah."],
    ["Too many attempts. Please try again in a few minutes.", "Terlalu banyak percobaan. Silakan coba lagi dalam beberapa menit."],
    ["Too many attempts. Please wait a few minutes and try again.", "Terlalu banyak percobaan. Tunggu beberapa menit lalu coba lagi."],
    ["This email is already registered. Please sign in.", "Email ini sudah terdaftar. Silakan masuk."],
    ["New sign-ups are disabled for this project.", "Pendaftaran baru dinonaktifkan untuk proyek ini."],
    ["Google sign-in is not set up in InsForge yet (Authentication > Auth Methods > Google).", "Masuk dengan Google belum diatur di InsForge (Authentication > Auth Methods > Google)."],
    ["Could not reach the Fruit Lens server.", "Tidak dapat menjangkau server Fruit Lens."],
    ["Could not reach InsForge. Check INSFORGE_URL and your internet connection.", "Tidak dapat menjangkau InsForge. Periksa INSFORGE_URL dan koneksi internet Anda."],
    ["InsForge returned an unexpected response.", "InsForge mengembalikan respons yang tidak terduga."],
    ["InsForge is not configured. Add INSFORGE_URL and INSFORGE_ANON_KEY to your .env file.", "InsForge belum dikonfigurasi. Tambahkan INSFORGE_URL dan INSFORGE_ANON_KEY ke file .env Anda."],
    ["InsForge is not configured. Add INSFORGE_URL to your .env file (see README).", "InsForge belum dikonfigurasi. Tambahkan INSFORGE_URL ke file .env Anda (lihat README)."],
    ["Connect InsForge first (see README).", "Hubungkan InsForge terlebih dahulu (lihat README)."],
    ["Turn on Google in InsForge: Authentication > Auth Methods > Google.", "Aktifkan Google di InsForge: Authentication > Auth Methods > Google."]
  ];

  var MAP = Object.create(null);
  function norm(s) { return s.replace(/\s+/g, " ").trim(); }
  PAIRS.forEach(function (p) { MAP[norm(p[0])] = p[1]; });

  /* ------------------------------------------------------------------ */
  /* Patterns: text that contains numbers or names                      */
  /* ------------------------------------------------------------------ */
  function T(s) { var r = tr(s); return r === null ? s : r; }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

  function unit(s) { // "3-6 Days" -> "3-6 Hari"
    return s.replace(/\b(Days?|days?)\b/g, function (m) { return m.charAt(0) === "D" ? "Hari" : "hari"; })
            .replace(/\b(Weeks?|weeks?)\b/g, function (m) { return m.charAt(0) === "W" ? "Minggu" : "minggu"; })
            .replace(/\b(Hours?|hours?)\b/g, function (m) { return m.charAt(0) === "H" ? "Jam" : "jam"; });
  }

  function policyParts(text) { // "at least 8 characters, a number, ..." -> Indonesian list
    return text.split(/,\s*/).map(function (part) {
      var p = part.trim(), m;
      if ((m = p.match(/^at least (\d+) characters$/i))) return "minimal " + m[1] + " karakter";
      var key = p.toLowerCase();
      return ({ "a number": "angka", "a lowercase letter": "huruf kecil", "an uppercase letter": "huruf besar", "a special character": "karakter khusus" })[key] || p;
    }).join(", ");
  }

  var PATTERNS = [
    [/^(\d+) scans? saved$/, function (m) { return m[1] + " pindaian tersimpan"; }],
    [/^(\d+) scans?$/, function (m) { return m[1] + " pindaian"; }],
    [/^(\d+) this week(.*)$/, function (m) { return m[1] + " minggu ini" + m[2]; }],
    [/^(\d+(?:\.\d+)?)% of scans$/, function (m) { return m[1] + "% dari pindaian"; }],
    [/^(\d+(?:\.\d+)?)% still maturing$/, function (m) { return m[1] + "% masih dalam pematangan"; }],
    [/^Freshness (\d+(?:\.\d+)?)%$/, function (m) { return "Kesegaran " + m[1] + "%"; }],
    [/^Your (.+) scans$/, function (m) { return "Pindaian " + T(m[1]) + " Anda"; }],
    [/^Scan a (.+)$/, function (m) { return "Pindai " + T(cap(m[1])); }],
    [/^(Unripe|Ripe|Rotten) Condition$/, function (m) { return "Kondisi " + T(m[1]); }],
    [/^(.+) \(Current\)$/, function (m) { return T(m[1]) + " (Saat Ini)"; }],
    [/^(.+) · (Tropical|Fruit vegetable|Citrus)$/, function (m) { return m[1] + " · " + T(m[2]); }],
    [/^Discard your (.+)$/, function (m) { return "Buang " + T(m[1]) + " Anda"; }],
    [/^Eat your (.+) soon$/, function (m) { return "Segera konsumsi " + T(m[1]) + " Anda"; }],
    [/^Your (.+) is still maturing$/, function (m) { return T(m[1]) + " Anda masih dalam pematangan"; }],
    [/^Latest scan: ripe, about (.+?) left\.\s*(.*)$/, function (m) { return "Pindaian terakhir: matang, sisa sekitar " + unit(m[1]) + ". " + T(m[2]); }],
    [/^Estimated (.+?) to ripen\.\s*(.*)$/, function (m) { return "Perkiraan " + unit(m[1]) + " hingga matang. " + T(m[2]); }],
    [/^Running the (.+) ripeness model$/, function (m) { return "Menjalankan model kematangan " + T(cap(m[1])); }],
    [/^No fruit matches "(.*)"\.$/, function (m) { return "Tidak ada buah yang cocok dengan \"" + m[1] + "\"."; }],
    [/^Could not use the camera: (.*)$/, function (m) { return "Tidak dapat menggunakan kamera: " + m[1]; }],
    [/^Request failed \((\d+)\)$/, function (m) { return "Permintaan gagal (" + m[1] + ")"; }],
    [/^The (.+) model could not process this image: (.*)$/, function (m) { return "Model " + T(cap(m[1])) + " tidak dapat memproses gambar ini: " + m[2]; }],
    [/^InsForge returned an error \(HTTP (\d+)\)\.$/, function (m) { return "InsForge mengembalikan kesalahan (HTTP " + m[1] + ")."; }],
    [/^We sent a verification link to (.+)\.$/, function (m) { return "Kami mengirim tautan verifikasi ke " + m[1] + "."; }],
    [/^We sent a 6-digit code to (.+)\.$/, function (m) { return "Kami mengirim kode 6 digit ke " + m[1] + "."; }],
    [/^Password needs (.+)\.$/, function (m) { return "Kata sandi harus memiliki " + policyParts(m[1]) + "."; }],
    [/^Use (at least .+)\.$/, function (m) { return "Gunakan " + policyParts(m[1]) + "."; }],
    [/^(At least .+)\.$/, function (m) { return cap(policyParts(m[1])) + "."; }],
    [/^Good (Morning|Afternoon|Evening)(.*)$/, function (m) { return { Morning: "Selamat Pagi", Afternoon: "Selamat Siang", Evening: "Selamat Sore" }[m[1]] + m[2]; }],
    [/^(\d+(?:\s*[-–]\s*\d+)?)\s+(days?|weeks?|hours?)$/i, function (m) { return unit(m[1] + " " + m[2]); }]
  ];

  function tr(text) {
    var key = norm(text);
    if (!key) return null;
    if (MAP[key] !== undefined) return MAP[key];
    for (var i = 0; i < PATTERNS.length; i++) {
      var m = key.match(PATTERNS[i][0]);
      if (m) return PATTERNS[i][1](m);
    }
    return null;
  }

  /* ------------------------------------------------------------------ */
  /* DOM translation with restore                                       */
  /* ------------------------------------------------------------------ */
  var SKIP = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1 };
  var ATTRS = ["placeholder", "title", "aria-label", "alt"];
  var textRec = new WeakMap(); // text node -> {en, shown}

  function compute(en) { // the text to show for an original English string, in the current language
    if (lang === "en") return en;
    var t = tr(en);
    if (t === null) return en;
    return en.match(/^\s*/)[0] + t + en.match(/\s*$/)[0];
  }

  function skipped(node) {
    for (var el = node.parentNode; el && el.nodeType === 1; el = el.parentNode) {
      if (SKIP[el.nodeName] || el.hasAttribute("data-no-i18n")) return true;
    }
    return false;
  }

  function doText(node) {
    var cur = node.nodeValue;
    if (!cur || !cur.trim() || skipped(node)) return;
    var rec = textRec.get(node);
    if (rec && cur === rec.shown) { // still the text we put there: re-evaluate for the current language
      var want = compute(rec.en);
      if (want !== cur) { node.nodeValue = want; rec.shown = want; }
      return;
    }
    // new text, or the app replaced the value: treat it as a new original
    var shown = compute(cur);
    textRec.set(node, { en: cur, shown: shown });
    if (shown !== cur) node.nodeValue = shown;
  }

  function doAttr(el, name) {
    var cur = el.getAttribute(name);
    if (cur === null || !cur.trim() || el.closest("[data-no-i18n]")) return;
    var recs = el.__flAttr || (el.__flAttr = {});
    var rec = recs[name];
    if (rec && cur === rec.shown) {
      var want = compute(rec.en);
      if (want !== cur) { el.setAttribute(name, want); rec.shown = want; }
      return;
    }
    var shown = compute(cur);
    recs[name] = { en: cur, shown: shown };
    if (shown !== cur) el.setAttribute(name, shown);
  }

  function doTree(root) {
    if (!root) return;
    if (root.nodeType === 3) { doText(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
    if (root.nodeType === 1) {
      if (SKIP[root.nodeName]) return;
      ATTRS.forEach(function (a) { if (root.hasAttribute(a)) doAttr(root, a); });
    }
    var w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, null);
    var n;
    while ((n = w.nextNode())) {
      if (n.nodeType === 3) doText(n);
      else if (!SKIP[n.nodeName]) ATTRS.forEach(function (a) { if (n.hasAttribute(a)) doAttr(n, a); });
    }
  }

  var observer = new MutationObserver(function (list) {
    list.forEach(function (r) {
      if (r.type === "childList") r.addedNodes.forEach(doTree);
      else if (r.type === "characterData") doText(r.target);
      else if (r.type === "attributes") doAttr(r.target, r.attributeName);
    });
  });
  observer.observe(document, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });

  /* ------------------------------------------------------------------ */
  /* Public API + language picker                                       */
  /* ------------------------------------------------------------------ */
  function syncPickers() {
    document.documentElement.setAttribute("lang", lang);
    document.querySelectorAll("[data-lang-set]").forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-lang-set") === lang ? "true" : "false");
    });
  }

  function setLang(next) {
    if (LANGS.indexOf(next) < 0 || next === lang) return;
    lang = next;
    try { localStorage.setItem(KEY, lang); } catch (e) {}
    doTree(document);
    syncPickers();
    try { window.dispatchEvent(new CustomEvent("fl-lang", { detail: lang })); } catch (e) {}
  }

  window.I18N = {
    get lang() { return lang; },
    setLang: setLang,
    t: function (s) { return lang === "en" ? s : T(s); },
    locale: function () { return lang === "id" ? "id-ID" : "en-US"; }
  };

  // Picker buttons: any element with data-lang-set="id|en". Capture phase so menus that stop clicks still work.
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-lang-set]");
    if (b) { e.preventDefault(); setLang(b.getAttribute("data-lang-set")); }
  }, true);

  var css = document.createElement("style");
  css.textContent =
    ".fl-lang{display:inline-flex;gap:2px;padding:3px;border-radius:999px;background:rgba(127,127,127,.18)}" +
    ".fl-lang button{border:0;background:transparent;color:inherit;font:inherit;font-size:11px;font-weight:700;padding:5px 12px;border-radius:999px;cursor:pointer;opacity:.75;min-height:30px}" +
    ".fl-lang.fl-wide{display:flex;width:100%}.fl-lang.fl-wide button{flex:1}" +
    ".fl-lang button[aria-pressed=true]{background:#e67e22;color:#fff;opacity:1}";
  (document.head || document.documentElement).appendChild(css);

  function ready() { doTree(document); syncPickers(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready);
  else ready();
  syncPickers();
})();
