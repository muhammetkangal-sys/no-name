# Git Versiyon Kontrolü Kullanım Rehberi

Bu rehber, `AI_CNC_Inspector` projenizde kaydettiğimiz versiyonlara (durumlara) nasıl geri dönebileceğinizi ve Git'i nasıl kullanacağınızı açıklar. Projede bir şeyler bozulduğunda veya eski çalışan haline dönmek istediğinizde bu komutlar hayat kurtarır.

> **Not:** Bu komutları **Komut İstemi (CMD)** veya IDE'nizin terminalinde proje klasörünün içindeyken (`C:\Users\user\Desktop\AI_CNC_Inspector`) çalıştırmalısınız.

---

## 1. Geçmiş Versiyonları Görmek

Projede bugüne kadar aldığımız tüm kayıtları (commit'leri) listelemek için:

```cmd
git log --oneline
```
Bu komut size şöyle bir çıktı verir:
```text
e147f4e (HEAD -> master) v0.2: YOLO entegrasyonu ve Isci Arayuzu tasarimi tamamlandi
a92b3c1 v0.1: Ilk kurulum
```
Buradaki `e147f4e` gibi 7 haneli kodlar, o versiyonun **kimlik numarasıdır (Hash)**. Eski bir versiyona dönmek için bu koda ihtiyacınız olacak.

---

## 2. Projede Yaptığınız Son Değişiklikleri İptal Etmek (Geri Almak)

Eğer kodlarda bir şeyler denediyseniz ama bozulduysa ve **son kaydettiğimiz (commit ettiğimiz) temiz hale dönmek** istiyorsanız:

```cmd
git restore .
```
*(Dikkat: Bu komut, son commit'ten sonra yaptığınız ve henüz kaydetmediğiniz tüm kod değişikliklerini siler ve projeyi en son çalışan haline döndürür.)*

---

## 3. Eski Bir Versiyona Göz Atmak (Zaman Yolculuğu)

Eğer örneğin 1 ay önceki bir versiyonun kodlarına bakmak istiyorsanız, `git log` ile öğrendiğiniz o 7 haneli kodu kullanarak zamanda geriye gidebilirsiniz:

```cmd
git checkout e147f4e
```
Bu komutu yazdığınızda proje klasörünüzdeki dosyalar bir anda o eski tarihteki haline dönüşür.

**Günümüze (en son güncel versiyona) geri dönmek için:**
```cmd
git checkout master
```
*(Bazı sistemlerde `master` yerine `main` kullanılır. Eğer hata verirse `git checkout main` yazabilirsiniz.)*

---

## 4. Yeni Bir Versiyon Kaydetmek (Yedeklemek)

Projede yeni bir özellik eklediniz ve her şey çok güzel çalışıyor. Bunu yeni bir versiyon olarak mühürlemek (kaydetmek) için sırayla şu komutları yazın:

1. Önce değişen dosyaları hazırlayın:
   ```cmd
   git add .
   ```
2. Sonra bu versiyona bir isim vererek kaydedin:
   ```cmd
   git commit -m "v0.3: Yeni bir ozellik eklendi, her sey calisiyor"
   ```

---

## Özet Kurtarma Senaryosu
*"Kodlarla oynadım, her şey bozuldu. Lütfen son çalışan kayda geri dön!"*
```cmd
git restore .
```
*(Eğer yeni eklediğiniz ama git'in henüz takip etmediği dosyalar da varsa ve onları da tamamen silip tertemiz yapmak isterseniz ekstra olarak `git clean -fd` yazabilirsiniz.)*
