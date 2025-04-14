{
  description = "Dev env for OnSIDES, including tabula, uv, pandoc, snakemake, etc.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.uv
            pkgs.jdk11
            pkgs.pandoc
            pkgs.duckdb
          ];

          shellHook = ''
            export JAVA_HOME=${pkgs.jdk11}/lib/openjdk
            export TABULA_JAVA_PATH=${pkgs.jdk11}/lib/openjdk/bin/java
            echo
            if [ ! -d ".venv" ]; then
              echo "Creating new virtual environment with uv..."
              ${pkgs.uv}/bin/uv sync
            fi

            source .venv/bin/activate

            test_tabula() {
              python -c "import tabula" >/dev/null 2>&1
              if [ $? -eq 0 ]; then
                echo "Onsides development environment activated!"
              else
                echo "There was an error installing tabula. Please check your installation."
              fi
            }
            test_tabula

            echo "To install additional Python packages:"
            echo "  uv add <package-name>"
            echo "To install additional non-Python packages, modify flake.nix."
            echo ""
          '';
        };
      }
    );
}
