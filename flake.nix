{
  description = "Python environment with tabula-py and uv package manager";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.uv  # Add uv package manager
            pkgs.jdk11  # Java is required for tabula-py
            pkgs.pandoc # For some random conversions (e.g. HTML -> TXT)
          ];

          shellHook = ''
            export JAVA_HOME=${pkgs.jdk11}/lib/openjdk
            export TABULA_JAVA_PATH=${pkgs.jdk11}/lib/openjdk/bin/java

            # Create a virtual environment if it doesn't exist
            if [ ! -d ".venv" ]; then
              echo "Creating new virtual environment with uv..."
              ${pkgs.uv}/bin/uv sync
            fi

            # Activate the virtual environment
            source .venv/bin/activate

            # Print helpful information when entering the shell
            echo "Onsides development environment activated!"
            echo "You can run your commands with:"
            echo "  uv run onsides"
            echo ""
            echo "To install additional packages:"
            echo "  uv pip install <package-name>"
            echo ""
            echo "To verify tabula-py installation:"
            echo "  python -c 'import tabula; print(tabula.__version__)'"
          '';
        };
      });
}
