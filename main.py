"""PixelForge command-line entry point."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if (ROOT / ".deps").is_dir():
    sys.path.insert(0, str(ROOT / ".deps"))


def parser() -> argparse.ArgumentParser:
    app = argparse.ArgumentParser(description="PixelForge: local pixel art production")
    commands = app.add_subparsers(dest="command", required=True)
    for name, help_text in [("demo", "Build the offline acceptance demo"),
                            ("build", "Produce pixel assets from a specification")]:
        command = commands.add_parser(name, help=help_text)
        if name == "build":
            source = command.add_mutually_exclusive_group(required=True)
            source.add_argument("--spec", type=Path, help="JSON production specification")
            source.add_argument("--prompt", help="City-walk demo brief (legacy)")
        command.add_argument("--output", type=Path, help="Destination directory")
        command.add_argument("--aseprite", type=Path,
                             default=Path(r"D:\Steam\steamapps\common\Aseprite\Aseprite.exe"))
        command.add_argument("--no-aseprite", action="store_true", help="Skip native Aseprite export")
        command.add_argument("--llm", action="store_true", help="Explicitly enable paid OpenAI calls")
        command.add_argument("--langgraph", action="store_true", help="Use the optional LangGraph runner")
    commands.add_parser("doctor", help="Inspect dependencies and configured tools")
    serve = commands.add_parser("serve", help="Start local FastAPI service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    return app


def main(argv: list[str] | None = None) -> int:
    app = parser()
    args = app.parse_args(argv)
    if args.command == "doctor":
        import importlib.util
        packages = {name: importlib.util.find_spec(name) is not None for name in
                    ("PIL", "fastapi", "uvicorn", "openai", "langgraph", "imageio_ffmpeg")}
        result = {"python": sys.executable, "packages": packages,
                  "aseprite": Path(r"D:\Steam\steamapps\common\Aseprite\Aseprite.exe").is_file(),
                  "openai_key_configured": bool(os.getenv("OPENAI_API_KEY")),
                  "mode": "offline unless --llm is explicitly provided"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if packages["PIL"] else 1
    if args.command == "serve":
        try:
            import uvicorn
        except ImportError:
            print("Install requirements-optional.txt to serve the API.", file=sys.stderr)
            return 1
        uvicorn.run("api:app", host=args.host, port=args.port, app_dir=str(ROOT))
        return 0
    try:
        if args.command == "build" and args.spec is not None:
            if args.no_aseprite or args.llm or args.langgraph:
                app.error("--spec uses local Aseprite. --no-aseprite, --llm and --langgraph are demo options.")
            if args.output is None:
                app.error("--spec requires --output pointing to a new version directory")
            from pixelforge.production import run_production
            result = run_production(args.spec, args.output, args.aseprite)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        from pixelforge.agents.planner import DEMO_PROMPT
        from pixelforge.pipeline import run_pipeline
        if args.langgraph:
            os.environ["PIXELFORGE_USE_LANGGRAPH"] = "1"
        result = run_pipeline(
            prompt=DEMO_PROMPT if args.command == "demo" else args.prompt,
            output=(args.output or ROOT / "output").resolve(),
            aseprite=None if args.no_aseprite else args.aseprite,
            use_llm=args.llm,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except (RuntimeError, ValueError, OSError, ImportError) as exc:
        print(f"PixelForge: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
