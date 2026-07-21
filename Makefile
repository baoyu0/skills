# baoyu0/skills — Install CLI tools to ~/bin/

BINDIR = $(HOME)/bin

SCRIPTS_PY = \
	tools/search-all/scripts/search-all.py \
	content-publishing/x-clip-purify/scripts/x-clip-purify.py \
	network/karing-routing/scripts/karing-route.py

SCRIPTS_SH = \
	tools/search-all/scripts/search-all.sh \
	content-publishing/x-clip-purify/scripts/x-clip-purify.sh \
	network/karing-routing/scripts/karing-route.sh \
	integration/hermes-memory-bridge/scripts/hermes-sync.sh

.PHONY: install
install: $(BINDIR)
	@echo "Installing CLI tools to $(BINDIR)..."
	$(foreach s,$(SCRIPTS_PY),cp "$(s)" "$(BINDIR)/" &&)
	$(foreach s,$(SCRIPTS_SH),cp "$(s)" "$(BINDIR)/" &&)
	@echo "Done. Make sure $(BINDIR) is in your PATH."

$(BINDIR):
	mkdir -p $@

.PHONY: list
list:
	@echo "Python scripts:"
	@for f in $(SCRIPTS_PY); do echo "  $$f"; done
	@echo "Shell wrappers:"
	@for f in $(SCRIPTS_SH); do echo "  $$f"; done

.PHONY: help
help:
	@echo "Usage: make install   — Copy CLI tools to ~/bin/"
	@echo "       make list      — List all CLI tools"
	@echo "       make help      — Show this help"
