{
  description = "Python environment with tabula-py and uv package manager using Fish shell";

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
          # Provide fish in the environment
          buildInputs = [
            pkgs.fish
            pkgs.uv
            pkgs.jdk11
            pkgs.pandoc
          ];

          # Even though we say "shell = fish", the shellHook is still parsed by Bash!
          # So we keep our shellHook in Bash syntax, then manually exec fish:
          shell = "${pkgs.fish}/bin/fish";

          shellHook = ''
            # -- Bash syntax for environment exports:
            export JAVA_HOME=${pkgs.jdk11}/lib/openjdk
            export TABULA_JAVA_PATH=${pkgs.jdk11}/lib/openjdk/bin/java

            if [ ! -d ".venv" ]; then
              echo "Creating new virtual environment with uv..."
              ${pkgs.uv}/bin/uv sync
            fi

            # At this point, we forcibly replace Bash with Fish. The `-C` argument
            # lets us specify some Fish code to run immediately upon starting.
            #
            # Within that Fish code, we can safely use 'source .venv/bin/activate.fish'
            # to activate the venv the proper Fish way, and then echo any helpful tips.

            exec ${pkgs.fish}/bin/fish -C '
              set fish_greeting
              function fish_prompt
                set_color green
                echo -n (prompt_pwd)
                set_color normal
                echo -n "> "
              end

              source .venv/bin/activate.fish

              echo "Onsides development environment activated!"
              echo "To install additional packages:"
              echo "  uv add <package-name>"
              echo ""
              echo "To verify tabula-py installation:"
              echo "  python -c \"import tabula; print(tabula.__version__)\""
            '
          '';
        };
      });
}
