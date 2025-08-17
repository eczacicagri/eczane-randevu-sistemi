# randevu/forms.py (TAM VE GÜNCEL HALİ)

from django import forms
from django.contrib.auth.models import User
from .models import TemsilciProfili, Urun, Teklif

class KayitFormu(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Şifre")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Şifre (Tekrar)")

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email')
        labels = {
            'first_name': 'Ad',
            'last_name': 'Soyad',
            'username': 'Kullanıcı Adı',
            'email': 'E-posta',
        }

    def __init__(self, *args, **kwargs):
        super(KayitFormu, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password != password_confirm:
            raise forms.ValidationError("Şifreler eşleşmiyor!")

        return cleaned_data


class TemsilciProfiliFormu(forms.ModelForm):
    class Meta:
        model = TemsilciProfili
        fields = ('telefon', 'firma', 'ozel_gun_notu', 'sorumlu_oldugu_urunler')
        labels = {
            'telefon': 'Telefon Numaranız',
            'firma': 'Çalıştığınız Firma',
            'ozel_gun_notu': 'Özel Günler İçin Not',
            'sorumlu_oldugu_urunler': 'Sorumlu Olduğunuz Ürünleri Seçin'
        }
        widgets = {
            'sorumlu_oldugu_urunler': forms.CheckboxSelectMultiple
        }

    def __init__(self, *args, **kwargs):
        super(TemsilciProfiliFormu, self).__init__(*args, **kwargs)
        if self.instance and self.instance.firma:
            self.fields['sorumlu_oldugu_urunler'].queryset = Urun.objects.filter(firma=self.instance.firma)
        else:
            self.fields['sorumlu_oldugu_urunler'].queryset = Urun.objects.none()


class TopluRandevuFormu(forms.Form):
    tarih = forms.DateField(
        label="Randevuların Açılacağı Tarih",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    baslangic_saati = forms.TimeField(
        label="Başlangıç Saati",
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    bitis_saati = forms.TimeField(
        label="Bitiş Saati",
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    aralik = forms.IntegerField(
        label="Randevu Aralığı (dakika cinsinden)",
        min_value=5,
        initial=15
    )

class TeklifFormu(forms.ModelForm):
    class Meta:
        model = Teklif
        fields = ['urun', 'mal_fazlasi_sarti', 'ekstra_iskonto', 'eczaci_degerlendirmesi']

    def __init__(self, *args, **kwargs):
        temsilci_user = kwargs.pop('user', None)
        super(TeklifFormu, self).__init__(*args, **kwargs)
        if temsilci_user:
            self.fields['urun'].queryset = temsilci_user.temsilciprofili.sorumlu_oldugu_urunler.all()
        else:
            self.fields['urun'].queryset = Urun.objects.none()