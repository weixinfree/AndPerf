pip3 uninstall andperf

rm -fr build
rm -fr dist
rm -fr andperf.egg-info

python3 setup.py sdist bdist_wheel

twine upload dist/*

sleep 5
pip3 install andperf