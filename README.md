# Build Python Flask 2 Apps with CodeSpace

This is a demo repo for The Flask Mega-Tutorial (https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world) in CodeSpace.

## Build Python Flask 2 Apps with CodeSpace Play list

[![Build Python Flask 2 Apps with CodeSpace](https://img.youtube.com/vi/a2D4bY0jEI0/0.jpg)](https://www.youtube.com/watch?v=a2D4bY0jEI0&list=PLtgJR0xD2TPeVeq6azvnKXYSeYHFzGaMi&index=1 "Build Python Flask 2 Apps with CodeSpace")


## How to work on this lab exercises?

CodeSpace is now free for everyone for 90 hours per month so you can use CodeSpace to work on all lab exercises.
If you are not under GitHub Classroom.
1. Fork this repo into your GitHub.
2. Change the Lab branch such as Lab01.
3. Create CodeSpace for each lab branch.
4. Follow the video and work on the lab.
5. If you need to get the solution, you can compare LabXX branch to LabXX-Completed branch, then you will know the difference.


# How to create translation
Run following commands
```
cd app/
mkdir translations
pybabel extract -F babel.cfg -k lazy_gettext -o translations/messages.pot .
pybabel init -i translations/messages.pot -d translations -l en
pybabel init -i translations/messages.pot -d translations -l es
pybabel init -i translations/messages.pot -d translations -l zh
pybabel compile -d translations
```

# How to update translation
```
cd app/
pybabel update -i translations/messages.pot -d translations
```