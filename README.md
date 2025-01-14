# Audiblez: Create audiobooks from e-books

Audiblez converts .epub into .mp3 using high-quality and lightweight Kokoro-82M text-to-speech models.


# How to install

```
pip install  audiblez  		# via Python PIP

brew install audiblez 		# On MacOSX via homebrew

apt get install audiblez  	# On Ubuntu/Debian
```


# From sources

```
# Get the model
wget 
```


# How to run

`audiblez book.epub book.mp3`

# Change language

use `-l` to specify language, eg:

`audiblez -l en-gb book.epub book.mp3`

Kokoro supports these languages:

```
en-us
en-gb
fr-fr
```

# Change voice

