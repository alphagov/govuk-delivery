venv: venv/bin/activate

venv/bin/activate: requirements.txt
	test -d venv || virtualenv --no-site-packages venv
	./venv/bin/easy_install readline
	./venv/bin/pip install -Ur requirements.txt
	touch venv/bin/activate

test: venv
	PYTHONPATH=. ./venv/bin/nosetests

clean:
	rm -rf venv
