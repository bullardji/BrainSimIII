#!/usr/bin/env python3
"""BrainSimIII CLI Text Generation Tool

A command-line interface for text generation using the BrainSimIII framework.
Provides GPT integration, UKS knowledge querying, and batch processing capabilities.
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import textwrap

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from gpt import GPTClient
    from uks.uks import UKS
    from uks.thing_labels import ThingLabels
    from modules.module_handler import ModuleHandler
    from modules.module_gpt_info import ModuleGPTInfo
except ImportError as e:
    print(f"Error importing BrainSimIII modules: {e}")
    print("Make sure you're running from the python-port directory")
    sys.exit(1)


class TextGenerationConfig:
    """Configuration manager for text generation settings."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "text_gen_config.json"
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        default_config = {
            "gpt": {
                "model": "gpt-3.5-turbo",
                "api_key": None,
                "max_tokens": 150,
                "temperature": 0.7
            },
            "uks": {
                "auto_save": True,
                "knowledge_base": "knowledge.json"
            },
            "output": {
                "format": "text",
                "save_to_file": False,
                "output_dir": "generated_text"
            },
            "batch": {
                "max_concurrent": 3,
                "delay_between_requests": 1.0
            }
        }
        
        if Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults
                for section, values in default_config.items():
                    if section in loaded_config:
                        values.update(loaded_config[section])
                return default_config
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
                
        return default_config
        
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
            
    def get(self, section: str, key: str, default=None):
        """Get a configuration value."""
        return self.config.get(section, {}).get(key, default)
        
    def set(self, section: str, key: str, value: Any):
        """Set a configuration value."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value


class CLITextGenerator:
    """Main CLI text generation class."""
    
    def __init__(self, config: TextGenerationConfig):
        self.config = config
        self.gpt_client: Optional[GPTClient] = None
        self.uks: Optional[UKS] = None
        self.module_handler: Optional[ModuleHandler] = None
        self.gpt_module: Optional[ModuleGPTInfo] = None
        
        # Initialize components
        self.initialize_components()
        
    def initialize_components(self):
        """Initialize GPT client, UKS, and modules."""
        try:
            # Initialize GPT client
            api_key = self.config.get("gpt", "api_key") or os.getenv("OPENAI_API_KEY")
            if api_key:
                self.gpt_client = GPTClient(
                    api_key=api_key,
                    model=self.config.get("gpt", "model", "gpt-3.5-turbo")
                )
                print(f"✅ GPT client initialized with model: {self.config.get('gpt', 'model')}")
            else:
                print("⚠️ No OpenAI API key found. GPT features will be limited.")
                
            # Initialize UKS
            self.uks = UKS()
            print("✅ UKS (Universal Knowledge Store) initialized")
            
            # Initialize module handler
            self.module_handler = ModuleHandler()
            
            # Initialize GPT info module
            if "ModuleGPTInfo" in self.module_handler.registry:
                self.gpt_module = self.module_handler.activate("ModuleGPTInfo")
                print("✅ GPT Info module activated")
                
        except Exception as e:
            print(f"❌ Error initializing components: {e}")
            
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using GPT."""
        if not self.gpt_client:
            return "Error: GPT client not available. Please configure API key."
            
        try:
            max_tokens = kwargs.get('max_tokens', self.config.get("gpt", "max_tokens", 150))
            result = self.gpt_client.generate(prompt, max_tokens=max_tokens)
            
            # Store in UKS for future reference
            if self.uks:
                try:
                    prompt_thing = self.uks.add_thing(f"prompt_{hash(prompt)}", "Prompt")
                    result_thing = self.uks.add_thing(f"result_{hash(result)}", "GeneratedText")
                    # Add relationship if method exists
                    if hasattr(self.uks, 'add_relationship'):
                        self.uks.add_relationship(prompt_thing, "generated", result_thing)
                except Exception:
                    pass  # Don't fail generation if UKS storage fails
                    
            return result
            
        except Exception as e:
            return f"Error generating text: {e}"
            
    def query_knowledge(self, query: str) -> List[str]:
        """Query the UKS knowledge base."""
        if not self.uks:
            return ["Error: UKS not available"]
            
        try:
            from uks.thing_labels import ThingLabels
            results = []
            
            # Search for things with labels matching the query
            query_words = query.lower().split()
            for word in query_words:
                thing = ThingLabels.get_thing(word)
                if thing:
                    results.append(f"Found: {thing.Label}")
                    
                    # Get relationships
                    if hasattr(thing, 'relationships') and thing.relationships:
                        for rel in thing.relationships[:5]:  # Limit to first 5
                            if hasattr(rel, 'target') and hasattr(rel.target, 'Label'):
                                rel_name = rel.reltype.Label if hasattr(rel.reltype, 'Label') else 'related_to'
                                results.append(f"  → {rel_name}: {rel.target.Label}")
                                
            # Also search in UKS list directly
            if hasattr(self.uks, 'UKSList'):
                for thing in self.uks.UKSList:
                    if any(word in thing.Label.lower() for word in query_words):
                        if f"Found: {thing.Label}" not in results:
                            results.append(f"Found: {thing.Label}")
                                
            if not results:
                results.append(f"No knowledge found for: {query}")
                
            return results
            
        except Exception as e:
            return [f"Error querying knowledge: {e}"]
            
    def batch_generate(self, prompts: List[str], output_file: Optional[str] = None) -> List[Dict[str, str]]:
        """Generate text for multiple prompts."""
        results = []
        
        print(f"Processing {len(prompts)} prompts...")
        
        for i, prompt in enumerate(prompts, 1):
            print(f"[{i}/{len(prompts)}] Generating...")
            
            result = self.generate_text(prompt.strip())
            
            entry = {
                "prompt": prompt.strip(),
                "generated_text": result,
                "timestamp": datetime.now().isoformat(),
                "model": self.config.get("gpt", "model", "unknown")
            }
            results.append(entry)
            
            # Add delay between requests
            import time
            delay = self.config.get("batch", "delay_between_requests", 1.0)
            if i < len(prompts):
                time.sleep(delay)
                
        # Save results if requested
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"✅ Results saved to: {output_file}")
            except Exception as e:
                print(f"❌ Could not save results: {e}")
                
        return results
        
    def interactive_mode(self):
        """Start interactive text generation session."""
        print("\n🤖 BrainSimIII Interactive Text Generation")
        print("=" * 50)
        print("Commands:")
        print("  /generate <prompt>  - Generate text")
        print("  /query <query>      - Query knowledge base") 
        print("  /knowledge          - Show knowledge stats")
        print("  /config             - Show configuration")
        print("  /save-config        - Save current config")
        print("  /help               - Show this help")
        print("  /quit               - Exit")
        print()
        
        while True:
            try:
                user_input = input("brainsim> ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.startswith('/quit'):
                    print("Goodbye!")
                    break
                    
                elif user_input.startswith('/generate '):
                    prompt = user_input[10:]
                    if prompt:
                        print(f"Generating text for: {prompt}")
                        result = self.generate_text(prompt)
                        print(f"Generated: {result}")
                    else:
                        print("Please provide a prompt")
                        
                elif user_input.startswith('/query '):
                    query = user_input[7:]
                    if query:
                        results = self.query_knowledge(query)
                        print("Knowledge results:")
                        for result in results:
                            print(f"  {result}")
                    else:
                        print("Please provide a query")
                        
                elif user_input.startswith('/knowledge'):
                    if self.uks:
                        stats = {
                            "total_things": len(self.uks.UKSList),
                            "total_relationships": len(getattr(self.uks, 'relationships', [])),
                        }
                        print(f"Knowledge base stats: {stats}")
                    else:
                        print("UKS not available")
                        
                elif user_input.startswith('/config'):
                    print("Current configuration:")
                    print(json.dumps(self.config.config, indent=2))
                    
                elif user_input.startswith('/save-config'):
                    self.config.save_config()
                    print(f"Configuration saved to: {self.config.config_file}")
                    
                elif user_input.startswith('/help'):
                    print("Commands:")
                    print("  /generate <prompt>  - Generate text")
                    print("  /query <query>      - Query knowledge base") 
                    print("  /knowledge          - Show knowledge stats")
                    print("  /config             - Show configuration")
                    print("  /save-config        - Save current config")
                    print("  /help               - Show this help")
                    print("  /quit               - Exit")
                    
                else:
                    # Treat as direct generation prompt
                    print(f"Generating text for: {user_input}")
                    result = self.generate_text(user_input)
                    print(f"Generated: {result}")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


def create_arg_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="BrainSimIII CLI Text Generation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          %(prog)s --generate "Write a story about AI"
          %(prog)s --query "artificial intelligence"
          %(prog)s --interactive
          %(prog)s --batch prompts.txt --output results.json
          %(prog)s --config --set-api-key your_key_here
        """)
    )
    
    # Generation options
    parser.add_argument("--generate", "-g", type=str,
                       help="Generate text from a single prompt")
    parser.add_argument("--query", "-q", type=str,
                       help="Query the knowledge base")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Start interactive mode")
    parser.add_argument("--batch", "-b", type=str,
                       help="Batch process prompts from file (one per line)")
    
    # Configuration options
    parser.add_argument("--config", "-c", action="store_true",
                       help="Show current configuration")
    parser.add_argument("--config-file", type=str, default="text_gen_config.json",
                       help="Configuration file path")
    parser.add_argument("--set-api-key", type=str,
                       help="Set OpenAI API key")
    parser.add_argument("--set-model", type=str,
                       help="Set GPT model (e.g., gpt-3.5-turbo, gpt-4)")
    
    # Output options
    parser.add_argument("--output", "-o", type=str,
                       help="Output file for results")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                       help="Output format")
    parser.add_argument("--max-tokens", type=int, default=150,
                       help="Maximum tokens to generate")
    
    # Processing options
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_arg_parser()
    args = parser.parse_args()
    
    # Initialize configuration
    config = TextGenerationConfig(args.config_file)
    
    # Handle configuration updates
    if args.set_api_key:
        config.set("gpt", "api_key", args.set_api_key)
        config.save_config()
        print(f"✅ API key updated and saved to {config.config_file}")
        
    if args.set_model:
        config.set("gpt", "model", args.set_model)
        config.save_config()
        print(f"✅ Model updated to {args.set_model}")
        
    if args.max_tokens != 150:
        config.set("gpt", "max_tokens", args.max_tokens)
        
    # Show configuration if requested
    if args.config:
        print("Current Configuration:")
        print("=" * 30)
        print(json.dumps(config.config, indent=2))
        return
        
    # Initialize text generator
    generator = CLITextGenerator(config)
    
    # Handle different modes
    if args.interactive:
        generator.interactive_mode()
        
    elif args.generate:
        print(f"Generating text for: {args.generate}")
        result = generator.generate_text(args.generate, max_tokens=args.max_tokens)
        
        if args.format == "json":
            output = {
                "prompt": args.generate,
                "generated_text": result,
                "timestamp": datetime.now().isoformat(),
                "model": config.get("gpt", "model")
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Generated Text:\n{result}")
            
        # Save to file if requested
        if args.output:
            try:
                with open(args.output, 'w') as f:
                    if args.format == "json":
                        json.dump(output, f, indent=2)
                    else:
                        f.write(result)
                print(f"✅ Output saved to: {args.output}")
            except Exception as e:
                print(f"❌ Could not save output: {e}")
                
    elif args.query:
        print(f"Querying knowledge base for: {args.query}")
        results = generator.query_knowledge(args.query)
        
        if args.format == "json":
            output = {
                "query": args.query,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            print(json.dumps(output, indent=2))
        else:
            print("Knowledge Results:")
            for result in results:
                print(f"  {result}")
                
    elif args.batch:
        if not Path(args.batch).exists():
            print(f"❌ Batch file not found: {args.batch}")
            return
            
        try:
            with open(args.batch, 'r') as f:
                prompts = [line.strip() for line in f.readlines() if line.strip()]
                
            if not prompts:
                print("❌ No prompts found in batch file")
                return
                
            print(f"Found {len(prompts)} prompts in batch file")
            
            results = generator.batch_generate(
                prompts, 
                output_file=args.output or f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            # Display summary
            print(f"\n📊 Batch Generation Complete:")
            print(f"   Prompts processed: {len(results)}")
            print(f"   Total tokens used: {sum(len(r['generated_text'].split()) for r in results)}")
            
        except Exception as e:
            print(f"❌ Error processing batch file: {e}")
            
    else:
        # No specific command, show help
        parser.print_help()
        print("\n💡 Try: --interactive to start an interactive session")
        print("💡 Or: --generate \"Your prompt here\" for quick generation")


if __name__ == "__main__":
    main()