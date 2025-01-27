#!/usr/bin/env python3

import requests
import json
import time
from datetime import datetime
import argparse
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich import box
import os

DUCO = "ᕲ"
DUCO_REST_API = "https://server.duinocoin.com"
CONFIG_FILE = "duino_config.txt"
console = Console()

def load_or_create_username():
    """Load username from config file or prompt user to create one"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            username = f.read().strip()
            if username:
                return username
    
    console.print("[yellow]No saved username found.[/yellow]")
    username = console.input("[bold cyan]Please enter your Duino-Coin username: [/bold cyan]")
    
    # Validate username before saving
    try:
        response = requests.get(f"{DUCO_REST_API}/v2/users/{username}")
        if response.status_code == 200 and response.json()["success"]:
            with open(CONFIG_FILE, 'w') as f:
                f.write(username)
            console.print(f"[green]Username saved successfully![/green]")
            return username
        else:
            console.print("[red]Invalid username. Please try again.[/red]")
            return load_or_create_username()
    except Exception as e:
        console.print(f"[red]Error validating username: {e}[/red]")
        return load_or_create_username()

class DuinoStats:
    def __init__(self, username):
        self.username = username
        self.balance = 0
        self.price_usd = 0
        self.balance_usd = 0
        self.previous_balances = []  # Lista para armazenar as últimas 10 atualizações de saldo
        
    def get_user_data(self):
        """Fetch user data from Duino-Coin API"""
        try:
            response = requests.get(f"{DUCO_REST_API}/v2/users/{self.username}")
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    return data["result"]
            return None
        except Exception as e:
            console.print(f"[red]Error fetching user data: {e}[/red]")
            return None

    def get_price(self):
        """Fetch current DUCO price"""
        try:
            response = requests.get(f"{DUCO_REST_API}/api.json")
            if response.status_code == 200:
                data = response.json()
                return data.get("Duco price", 0)
            return 0
        except Exception as e:
            console.print(f"[red]Error fetching price: {e}[/red]")
            return 0

    def format_hashrate(self, hashrate):
        """Format hashrate with appropriate units"""
        units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s"]
        unit_index = 0
        
        while hashrate > 1000 and unit_index < len(units) - 1:
            hashrate /= 1000
            unit_index += 1
            
        return f"{hashrate:.2f} {units[unit_index]}"

    def display_miners_table(self, miners):
        """Display miners information in a table without scrolling"""
        table = Table(title="Active Miners", box=box.ROUNDED)
        
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Software", style="magenta")
        table.add_column("Identifier", style="green")
        table.add_column("Hashrate", justify="right", style="yellow")
        table.add_column("Accepted", justify="right", style="green")
        table.add_column("Rejected", justify="right", style="red")
        table.add_column("Pool", style="blue")
        
        total_hashrate = 0
        total_accepted = 0
        total_rejected = 0
        
        for i, miner in enumerate(miners, 1):
            total_hashrate += miner.get("hashrate", 0)
            total_accepted += miner.get("accepted", 0)
            total_rejected += miner.get("rejected", 0)
            
            table.add_row(
                str(i),
                miner.get("software", ""),
                miner.get("identifier", ""),
                self.format_hashrate(miner.get("hashrate", 0)),
                str(miner.get("accepted", 0)),
                str(miner.get("rejected", 0)),
                miner.get("pool", "")
            )
        
        # Display the miners table directly without scrolling
        console.print(table)
        return total_hashrate, total_accepted, total_rejected

    def display_stats(self):
        """Display main statistics"""
        user_data = self.get_user_data()
        if not user_data:
            console.print("[red]Failed to fetch user data[/red]")
            return

        self.price_usd = self.get_price()
        self.balance = user_data.get("balance", {}).get("balance", 0)
        self.balance_usd = self.balance * self.price_usd

        # Adiciona o saldo atual à lista de saldos
        self.previous_balances.append(self.balance)
        if len(self.previous_balances) > 10:  # Mantém apenas as últimas 10 atualizações
            self.previous_balances.pop(0)

        # Cálculo de ganhos diários
        if len(self.previous_balances) > 1:
            daily_earnings = self.previous_balances[-1] - self.previous_balances[0]  # Diferença entre o saldo mais recente e o mais antigo
        else:
            daily_earnings = 0  # Se não houver saldos suficientes, ganhos diários é 0

        # Display user info
        console.print(Panel(
            f"[bold cyan]User:[/bold cyan] {self.username}\n"
            f"[bold green]Balance:[/bold green] {DUCO} {self.balance:.4f} (${self.balance_usd:.2f})\n"
            f"[bold yellow]DUCO Price:[/bold yellow] ${self.price_usd:.8f}\n"
            f"[bold blue]Verification:[/bold blue] {'Verified' if user_data.get('balance', {}).get('verified') == 'yes' else 'Not Verified'}\n"
            f"[bold magenta]Trust Score:[/bold magenta] {user_data.get('balance', {}).get('trust_score', 0)}\n"
            f"[bold green]Daily Earnings:[/bold green] {DUCO} {daily_earnings:.4f} (${daily_earnings * self.price_usd:.2f})",  # Exibindo ganhos diários
            title="Duino-Coin Statistics",
            border_style="green"
        ))

        # Display miners info
        miners = user_data.get("miners", [])
        if miners:
            total_hashrate, total_accepted, total_rejected = self.display_miners_table(miners)
            
            acceptance_rate = (total_accepted / (total_accepted + total_rejected) * 100) if (total_accepted + total_rejected) > 0 else 0
            
            console.print(Panel(
                f"[bold cyan]Total Hashrate:[/bold cyan] {self.format_hashrate(total_hashrate)}\n"
                f"[bold green]Acceptance Rate:[/bold green] {acceptance_rate:.2f}%\n"
                f"[bold yellow]Active Miners:[/bold yellow] {len(miners)}",
                title="Mining Statistics",
                border_style="blue"
            ))

def main(args):
    username = load_or_create_username()
    stats = DuinoStats(username)
    
    console.print("[bold green]Starting Duino-Coin Monitor...[/bold green]")
    
    def generate_content():
        """Generate content for live display"""
        content = Table.grid(padding=1, expand=True)
        content.add_column()
        
        content.add_row(Panel("[bold cyan]Duino-Coin Monitor[/bold cyan]", style="cyan"))
        content.add_row(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        user_data = stats.get_user_data()
        if user_data:
            stats.price_usd = stats.get_price()
            stats.balance = user_data.get("balance", {}).get("balance", 0)
            stats.balance_usd = stats.balance * stats.price_usd
            
            # Adiciona o saldo atual à lista de saldos
            stats.previous_balances.append(stats.balance)
            if len(stats.previous_balances) > 10:  # Mantém apenas as últimas 10 atualizações
                stats.previous_balances.pop(0)

            # Cálculo de ganhos diários
            if len(stats.previous_balances) > 1:
                daily_earnings = stats.previous_balances[-1] - stats.previous_balances[0]  # Diferença entre o saldo mais recente e o mais antigo
            else:
                daily_earnings = 0  # Se não houver saldos suficientes, ganhos diários é 0
            
            # User info panel
            content.add_row(Panel(
                f"[bold cyan]User:[/bold cyan] {stats.username}\n"
                f"[bold green]Balance:[/bold green] {DUCO} {stats.balance:.4f} (${stats.balance_usd:.2f})\n"
                f"[bold yellow]DUCO Price:[/bold yellow] ${stats.price_usd:.8f}\n"
                f"[bold blue]Verification:[/bold blue] {'Verified' if user_data.get('balance', {}).get('verified') == 'yes' else 'Not Verified'}\n"
                f"[bold magenta]Trust Score:[/bold magenta] {user_data.get('balance', {}).get('trust_score', 0)}\n"
                f"[bold green]Daily Earnings:[/bold green] {DUCO} {daily_earnings:.4f} (${daily_earnings * stats.price_usd:.2f})",  # Exibindo ganhos diários
                title="Duino-Coin Statistics",
                border_style="green"
            ))
            
            # Miners info
            miners = user_data.get("miners", [])
            if miners:
                # Miners table
                table = Table(title="Active Miners", box=box.ROUNDED)
                table.add_column("ID", justify="right", style="cyan")
                table.add_column("Software", style="magenta")
                table.add_column("Identifier", style="green")
                table.add_column("Hashrate", justify="right", style="yellow")
                table.add_column("Accepted", justify="right", style="green")
                table.add_column("Rejected", justify="right", style="red")
                table.add_column("Pool", style="blue")
                
                total_hashrate = 0
                total_accepted = 0
                total_rejected = 0
                
                for i, miner in enumerate(miners, 1):
                    total_hashrate += miner.get("hashrate", 0)
                    total_accepted += miner.get("accepted", 0)
                    total_rejected += miner.get("rejected", 0)
                    
                    table.add_row(
                        str(i),
                        miner.get("software", ""),
                        miner.get("identifier", ""),
                        stats.format_hashrate(miner.get("hashrate", 0)),
                        str(miner.get("accepted", 0)),
                        str(miner.get("rejected", 0)),
                        miner.get("pool", "")
                    )
                
                content.add_row(table)
                
                # Mining stats panel
                acceptance_rate = (total_accepted / (total_accepted + total_rejected) * 100) if (total_accepted + total_rejected) > 0 else 0
                content.add_row(Panel(
                    f"[bold cyan]Total Hashrate:[/bold cyan] {stats.format_hashrate(total_hashrate)}\n"
                    f"[bold green]Acceptance Rate:[/bold green] {acceptance_rate:.2f}%\n"
                    f"[bold yellow]Active Miners:[/bold yellow] {len(miners)}",
                    title="Mining Statistics",
                    border_style="blue"
                ))
        
        return content
    
    with Live(generate_content(), refresh_per_second=1/args.interval) as live:
        try:
            while True:
                live.update(generate_content())
                time.sleep(args.interval)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Monitor stopped by user[/bold yellow]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Duino-Coin CLI Monitor")
    parser.add_argument("-i", "--interval", help="Refresh interval in seconds", type=int, default=60) # default 60 seconds
    parser.add_argument("--reset", help="Reset saved username", action="store_true")
    args = parser.parse_args()

    if args.reset and os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        console.print("[yellow]Saved username has been reset.[/yellow]")

    main(args)