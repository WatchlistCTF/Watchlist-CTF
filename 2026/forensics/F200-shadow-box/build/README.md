# F200 build

`f200_build.py` writes the layered PDF: an original memo, then two incremental saves that change the author, strike a status word into an orphaned image, and add a phone-home script. The three planted findings assemble into the flag.

Needs `fontTools` and Pillow, and Poppins TTF weights in `/usr/share/fonts/truetype/google-fonts` (download from Google Fonts if rebuilding).
