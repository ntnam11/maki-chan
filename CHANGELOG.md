# Changelogs

## [0.3.0] - 2020-04-16
### Added
- new method to send long message (over 2000 characters)
- log file & logging module
#### New Commands
- `scout`
- `lyrics`
### Modified
- separated commands to multiple files for readability & maintainability
- code markdown in changelog
- increased `llradio` cache to 100 songs
### Bug fixed
- calling `llradio` twice cause `ClientException`
- `config` doesn't save the value

## [0.2.4] - 2020-04-10
### Added
- bot's status
#### New Commands
- `avatar`
- `config`
- `apistatus`
- `status`
### Modified
- `cardgame`: added llsif all stars
- llradio`: added cache system (50 songs)

## [0.2.3] - 2020-04-09
### Added
- bot sleep time
#### New Commands
- `loop`
- `choose`
### Modified
- `debug`
- `llradio` & commands check for sleep time

## [0.2.2] - 2020-04-07
### Added
#### New Commands
- `llradio`
- `stop`
### Bug fixed
- `songgame` plays radio drama
- `play`, `search` & all music related commands

## [0.2.1] - 2020-04-05
### Added
#### New Commands
- `listserver`
- `leaveserver`
- `songgame`
- `lyricgame`
### Modified
- `rename` songgame to lyricgame
### Bug fixed
- `randomcard` doesn't return expected result with capitalized query
- fixed `cat` command

## [0.2.0] - 2020-02-22
### Added
#### New Commands
- `songgame`
### Modified
- separated game commands to another file for readability & maintainability
- created a loop in run.py to prevent random crashes from Heroku
- created base testing (although it hasn't been used yet)

## [0.1.5] - 2020-01-31
### Added
#### New Commands
- `debug`
### Bug fixed
- `flush` causes `Exception`

## [0.1.4] - 2020-01-12
### Added
#### New Commands
- `message`

## [0.1.3] - 2019-12-13
### Added
#### New Commands
- `setavatar`
### Modified
- `cardgame` custom difficulty
### Bug fixed
- `cardgame` timeout bug (thanks to Uehara Ayumu#6011)
- `cardgame` allows negative number (thanks to Uehara Ayumu#6011)
- `music`: next song must be manually called

## [0.1.2] - 2019-09-08
### Added
- README.md
- LICENSE.md
#### New Commands
- LLSIF: `cardinfo`, `randomcard`, `idolinfo`
### Modified
- Some markdowns
- Help message
### Bug fixes
- Loading shared library on Heroku

## [0.1.1] - 2019-09-01
### Added
#### New Commands
- `changelog`
- `flush`
### Modified
- `help`
### Removed
- `restart`
- FFmpeg due to GitHub's recommended maximum file size

## [0.1.0] - 2019-08-31
### Added
- Searching & playing music
- Environment variable checking
- Owner-only decorator
- Youtube API key
#### New Commands
- music: `search`, `play`, `queue`, `np`, `skip`
- Special: `shutdown`, `restart` (untested)
### Modified
- Code efactoring
- Markdown
- `say` & `bigtext`: delete message after calling

## [0.0.2] - 2019-08-21
### Added
- Sample configuration
- Filter messages from self
- Opus loader
#### New Commands
- `cardgame`
- music: `join`, `leave`

## [0.0.1] - 2019-07-29
### Added
- Repository
#### New Commands
- `setprefix`
- `help`
- `say`
- `bigtext`
- `lenny`
- `cat`
- pics: `hug`, `cry`, `cuddle`, `kiss`, `lewd`, `nom`, `nyan`, `owo`, `pat`, `pout`, `slap`, `smug`, `stare`, `tickle`, `triggered`, `lick`
