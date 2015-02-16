from subprocess import call

afplay = "afplay wavs/{}"

hup = "WW_Tingle_Hup.wav"
yoop = "WW_Tingle_Yoop.wav"
kooloo = "WW_Tingle_KoolooLim.wav"
pah = "WW_Tingle_Pah.wav"

limpah = "MM_Tingle_Magic.wav"

grouch_wav = "WW_Tingle_Grouch.wav"

def kooloo_limpah():
    call(afplay.format(hup), shell=True)
    call(afplay.format(yoop), shell=True)
    call(afplay.format(kooloo), shell=True)
    call(afplay.format(pah), shell=True)

def magic():
    call(afplay.format(limpah), shell=True)

def grouch():
    call(afplay.format(grouch_wav), shell=True)
