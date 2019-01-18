[![Build Status](https://travis-ci.org/Leeps-Lab/oTree.svg?branch=master)](https://travis-ci.org/Leeps-Lab/oTree)

# LEEPS Lab oTree Experiments

## Quick start

```
> git clone --recurse-submodules https://github.com/Leeps-Lab/oTree.git
> cd oTree
> git submodule update --recursive --remote
> virtualenv -p `which python3` venv
> source venv/bin/activate
> pip install -r requirements.txt
> otree resetdb
> otree runserver
```

If you plan on modifying anything in any of the subrepos (that is, anything in the `bimatrix`, `imperfect_monitoring`, or `stochastic_bimatrix` folders), make sure you run `git checkout master` first in the subrepo you're modifying. If you don't, you may lose some work.

## Contact & support

[oTree Help & discussion mailing list](https://groups.google.com/forum/#!forum/otree)

* Contact mlgrant@ucsc.edu with experiment specific bug reports.
* Contact chris@otree.org with general oTree bug reports.

## Related repositories

* The oTree core libraries are at https://github.com/oTree-org/otree-core.
* The oTree experiment examples are at https://github.com/oTree-org/oTree.
* The oTree-Redwood extension library is at https://github.com/Leeps-Lab/otree-redwood.
