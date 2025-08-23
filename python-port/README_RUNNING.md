# Running BrainSimIII Python Port

This document describes the different ways to run the BrainSimIII Python port.

## Main Entry Point

The primary entry point is `main.py`, which provides access to all execution modes:

```bash
python3 main.py {gui|cli|text} [args...]
```

### 🖥️ GUI Mode
Launch the graphical user interface:
```bash
python3 main.py gui
```

### 🔧 CLI Mode  
Run the console version with module and network processing:
```bash
python3 main.py cli                    # Basic console mode
python3 main.py cli -- --ticks 10      # Run 10 simulation ticks
python3 main.py cli -- project.xml     # Load a project file
python3 main.py cli -- --help          # Show CLI help
```

### 📝 Text Generation Mode
Access the AI text generation features:
```bash
python3 main.py text -- --interactive              # Interactive mode
python3 main.py text -- --generate "Hello AI"      # Generate text
python3 main.py text -- --query "artificial intelligence"  # Query knowledge
python3 main.py text -- --help                     # Show text generator help
```

## Direct Entry Points

You can also run components directly:

### GUI Application
```bash
python3 app.py
```

### Console Launcher
```bash
python3 cli.py [project_file] [--ticks N]
```

### Text Generation CLI
```bash
python3 text_generator.py --interactive
python3 text_generator.py --generate "Your prompt here"
python3 text_generator.py --batch prompts.txt
python3 text_generator.py --query "search term"
```

## Text Generator Features

The text generation CLI supports:

- **Single generation**: `--generate "prompt"`
- **Interactive mode**: `--interactive` 
- **Batch processing**: `--batch file.txt`
- **Knowledge queries**: `--query "term"`
- **Configuration**: `--config`, `--set-api-key`, `--set-model`
- **Multiple formats**: `--format json` or `--format text`

### Interactive Commands
In interactive mode, use these commands:
- `/generate <prompt>` - Generate text
- `/query <term>` - Query knowledge base
- `/knowledge` - Show UKS statistics
- `/config` - Show current settings
- `/help` - Show help
- `/quit` - Exit

### Batch Processing
Create a text file with one prompt per line:
```
What is artificial intelligence?
Explain machine learning
How do neural networks work?
```

Then run: `python3 text_generator.py --batch prompts.txt --output results.json`

## Configuration

The text generator uses JSON configuration files. Set your OpenAI API key:
```bash
python3 text_generator.py --set-api-key your_key_here
```

## Requirements

- Python 3.8+
- tkinter (for GUI mode)
- OpenCV (optional, for advanced vision features)
- OpenAI API key (for text generation)