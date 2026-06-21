"""
Command-Line Interface for the Company Brochure Generator
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

from main import main as run_generator
from config import get_provider_summary, LLM_PROVIDER
from cache_manager import cache
from logger import logger

def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Company Brochure Generator - Generate professional company brochures using LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a brochure for a company
  python src/cli.py "Hugging Face" "https://huggingface.co"
  
  # Generate with specific output file
  python src/cli.py "Taylor Swift Store" "https://taylorswift.com" -o output/taylor.md
  
  # Clear cache
  python src/cli.py --clear-cache
  
  # Show cache statistics
  python src/cli.py --cache-stats
  
  # Run in verbose mode
  python src/cli.py "Company Name" "https://company.com" -v
        """
    )
    
    # Positional arguments
    parser.add_argument(
        "company_name",
        nargs="?",
        help="Name of the company"
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Company website URL"
    )
    
    # Optional arguments
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: auto-generated in output/)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached data"
    )
    parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="Show cache statistics"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show configuration information"
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai", "gemini"],
        help="Override the provider specified in .env"
    )
    
    return parser

def handle_cache_commands(args) -> bool:
    """
    Handle cache-related commands.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        True if a cache command was handled, False otherwise
    """
    if args.clear_cache:
        count = cache.clear()
        print(f"Cleared {count} cache files")
        return True
    
    if args.cache_stats:
        stats = cache.get_stats()
        print("\nCache Statistics:")
        print(f"  Total Files: {stats['total_files']}")
        print(f"  Total Size: {stats['total_size_mb']:.2f} MB")
        print(f"  Cache Directory: {stats['cache_dir']}")
        return True
    
    return False

def handle_info_command(args) -> bool:
    """
    Handle info command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        True if info command was handled, False otherwise
    """
    if args.info:
        print("\n" + "="*50)
        print("Company Brochure Generator - Configuration")
        print("="*50)
        print(get_provider_summary())
        print(f"\nCache Enabled: {cache.enabled}")
        print(f"Cache Expiry: {cache.expiry_days} days")
        print(f"Cache Directory: {cache.cache_dir}")
        print("="*50)
        return True
    
    return False

def main():
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Handle special commands
    if handle_cache_commands(args):
        return
    
    if handle_info_command(args):
        return
    
    # Validate required arguments
    if not args.company_name or not args.url:
        parser.print_help()
        print("\nError: Company name and URL are required unless using special commands")
        sys.exit(1)
    
    # Override provider if specified
    if args.provider:
        import os
        os.environ['LLM_PROVIDER'] = args.provider
        logger.info(f"Overriding provider to: {args.provider}")
    
    # Disable cache if requested
    if args.no_cache:
        cache.enabled = False
        logger.info("Caching disabled")
    
    # Run the generator
    try:
        # Import and run the main function
        from main import main as run_generator
        run_generator()
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()