.PHONY: help default install uninstall

help: default


default:
	@echo "install                install syncor to sys"
	@echo "uninstall              uninstall syncor"

install:
	ln -f syncor.py /usr/bin/syncor

uninstall:
	rm -f /usr/bin/syncor

