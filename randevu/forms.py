# randevu/forms.py 

from django import forms
from django.contrib.auth.models import User
from .models import TemsilciProfili

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
        fields = ('telefon', 'firma')
        labels = {
            'telefon': 'Telefon Numaranız',
            'firma': 'Çalıştığınız Firma',         
        }
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