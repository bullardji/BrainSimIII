#!/usr/bin/env python3
"""BrainSimIII Main Entry Point

This is the primary entry point for the BrainSimIII Python port. 
It provides options to run the system in different modes.
"""
import sys
import argparse
from pathlib import Path


def main():
    """Main entry point with mode selection."""
    parser = argparse.ArgumentParser(
        description="BrainSimIII - Brain Simulator III Python Port",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available modes:
  gui         Launch the graphical user interface
  cli         Run in command-line mode
  text        Text generation CLI tool
  
Examples:
  python main.py gui                    # Launch GUI
  python main.py cli project.xml       # Load project in CLI mode
  python main.py text --interactive    # Interactive text generation
  python main.py text --generate "Hello AI"  # Generate text
        """
    )
    
    parser.add_argument("mode", choices=["gui", "cli", "text"], 
                       help="Execution mode")
    parser.add_argument("args", nargs="*", 
                       help="Arguments to pass to the selected mode")
    
    # Handle help for subcommands
    if len(sys.argv) > 2 and "--help" in sys.argv[2:]:
        mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ["gui", "cli", "text"] else None
        if mode == "cli":
            from cli import main as cli_main
            return cli_main(["--help"])
        elif mode == "text":
            from text_generator import main as text_main
            original_argv = sys.argv
            sys.argv = ["text_generator.py", "--help"]
            result = text_main()
            sys.argv = original_argv
            return result
    
    args = parser.parse_args()
    
    if args.mode == "gui":
        # Launch GUI mode
        try:
            from app import BrainSimApp
            print("🧠 Starting BrainSimIII GUI...")
            app = BrainSimApp()
            app.run()
        except ImportError as e:
            print(f"❌ GUI mode not available: {e}")
            print("Make sure tkinter is installed: pip install tkinter")
            return 1
        except Exception as e:
            print(f"❌ Error starting GUI: {e}")
            return 1
            
    elif args.mode == "cli":
        # Launch CLI mode
        try:
            from cli import main as cli_main
            print("🧠 Starting BrainSimIII CLI...")
            return cli_main(args.args)
        except Exception as e:
            print(f"❌ Error starting CLI: {e}")
            return 1
            
    elif args.mode == "text":
        # Launch text generation CLI
        try:
            from text_generator import main as text_main
            print("🧠 Starting BrainSimIII Text Generator...")
            # Override sys.argv for the text generator
            original_argv = sys.argv
            sys.argv = ["text_generator.py"] + args.args
            result = text_main()
            sys.argv = original_argv
            return result
        except Exception as e:
            print(f"❌ Error starting text generator: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())