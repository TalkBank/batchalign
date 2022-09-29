pip install .
make -C ./baln/opt/CLANUtils/src/ -f "makefile.$(UNAME)"
mv ./baln/opt/CLANUtils/unix/bin/* $PREFIX/bin
