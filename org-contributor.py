#!/usr/bin/env python3
"""
Monthly GitHub Contributor Analysis
Specialized script for analyzing contributor activity over the last month
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import argparse
import os
from collections import defaultdict

class MonthlyContributorAnalyzer:
    def __init__(self, token: str = None):
        """
        Initialize the monthly contributor analyzer
        
        Args:
            token: GitHub personal access token for authenticated requests
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Monthly-Contributor-Analyzer"
        }
        
        if token:
            self.headers["Authorization"] = f"token {token}"
        
        # Calculate date range for last month
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=90)
        self.since_iso = self.start_date.isoformat()
        self.until_iso = self.end_date.isoformat()
        
        print(f"Analyzing contributions from {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
    
    def get_organization_repos(self, org_name: str, repo_type: str = "all") -> List[str]:
        """Get all repositories from a GitHub organization"""
        print(f"Fetching repositories for organization: {org_name}")
        
        repos = []
        page = 1
        per_page = 100
        
        while True:
            url = f"{self.base_url}/orgs/{org_name}/repos"
            params = {
                "type": repo_type,
                "sort": "updated",
                "direction": "desc",
                "per_page": per_page,
                "page": page
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                page_repos = response.json()
                if not page_repos:
                    break
                
                for repo in page_repos:
                    # Only include repos that were updated in the last month
                    updated_at = datetime.fromisoformat(repo['updated_at'].replace('Z', '+00:00'))
                    if updated_at >= self.start_date.replace(tzinfo=updated_at.tzinfo):
                        repos.append(f"{org_name}/{repo['name']}")
                
                page += 1
                time.sleep(0.3)
            else:
                print(f"Error fetching organization repos: {response.status_code}")
                break
        
        print(f"Found {len(repos)} active repositories in {org_name}")
        return repos
    
    def get_monthly_commits(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get all commits from the last month for a repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"
        
        all_commits = []
        page = 1
        per_page = 100
        
        while True:
            params = {
                "since": self.since_iso,
                "until": self.until_iso,
                "per_page": per_page,
                "page": page
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                commits = response.json()
                if not commits:
                    break
                
                all_commits.extend(commits)
                page += 1
                
                # If we get less than per_page, we're done
                if len(commits) < per_page:
                    break
                    
                time.sleep(0.2)
            else:
                print(f"Error fetching commits for {owner}/{repo}: {response.status_code}")
                break
        
        return all_commits
    
    def get_user_details(self, username: str) -> Dict[str, Any]:
        """Get user profile details"""
        url = f"{self.base_url}/users/{username}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            user_data = response.json()
            return {
                "name": user_data.get("name"),
                "email": user_data.get("email"),
                "company": user_data.get("company"),
                "location": user_data.get("location"),
                "bio": user_data.get("bio"),
                "public_repos": user_data.get("public_repos", 0),
                "followers": user_data.get("followers", 0),
                "following": user_data.get("following", 0),
                "avatar_url": user_data.get("avatar_url"),
                "html_url": user_data.get("html_url")
            }
        
        return {}
    
    def analyze_monthly_contributors(self, org_name: str, repo_type: str = "all", 
                                   company_filter: str = None) -> Dict[str, Any]:
        """
        Analyze contributors for the last month across an organization
        
        Args:
            org_name: Organization name
            repo_type: Type of repositories to analyze
            company_filter: Filter contributors by company
        
        Returns:
            Dictionary containing monthly contributor analysis
        """
        print(f"Starting monthly contributor analysis for: {org_name}")
        
        # Get organization repositories
        org_repos = self.get_organization_repos(org_name, repo_type)
        
        if not org_repos:
            print(f"No active repositories found for organization: {org_name}")
            return {}
        
        # Track contributors and their activity
        contributors = defaultdict(lambda: {
            "commits": 0,
            "repositories": set(),
            "commit_details": [],
            "lines_added": 0,
            "lines_deleted": 0,
            "files_changed": set(),
            "commit_dates": []
        })
        
        total_commits = 0
        repo_activity = {}
        
        # Analyze each repository
        for repo_name in org_repos:
            print(f"Analyzing monthly commits in {repo_name}...")
            owner, repo = repo_name.split("/", 1)
            
            monthly_commits = self.get_monthly_commits(owner, repo)
            repo_activity[repo_name] = len(monthly_commits)
            total_commits += len(monthly_commits)
            
            for commit in monthly_commits:
                commit_data = commit.get("commit", {})
                author_data = commit.get("author", {})
                
                if not author_data:
                    continue
                
                username = author_data.get("login")
                if not username:
                    continue
                
                # Apply company filter if specified
                if company_filter and username not in contributors:
                    user_details = self.get_user_details(username)
                    user_company = user_details.get("company", "").strip().lower()
                    user_company = user_company.lstrip("@")
                    
                    if company_filter.lower() not in user_company:
                        continue
                
                # Track contributor activity
                contributors[username]["commits"] += 1
                contributors[username]["repositories"].add(repo_name)
                contributors[username]["commit_dates"].append(commit_data.get("author", {}).get("date"))
                
                # Store commit details
                commit_detail = {
                    "repository": repo_name,
                    "sha": commit.get("sha"),
                    "message": commit_data.get("message", "").split('\n')[0][:100],  # First line, truncated
                    "date": commit_data.get("author", {}).get("date"),
                    "url": commit.get("html_url")
                }
                contributors[username]["commit_details"].append(commit_detail)
            
            time.sleep(0.5)  # Rate limiting
        
        # Enrich contributor data with user details
        enriched_contributors = []
        
        for username, activity in contributors.items():
            print(f"Enriching data for contributor: {username}")
            
            user_details = self.get_user_details(username)
            
            # Apply company filter if not already applied
            if company_filter:
                user_company = user_details.get("company", "").strip().lower()
                user_company = user_company.lstrip("@")
                
                if company_filter.lower() not in user_company:
                    continue
            
            contributor_data = {
                "username": username,
                "name": user_details.get("name") or username,
                "email": user_details.get("email"),
                "company": user_details.get("company"),
                "location": user_details.get("location"),
                "bio": user_details.get("bio"),
                "avatar_url": user_details.get("avatar_url"),
                "profile_url": user_details.get("html_url"),
                "public_repos": user_details.get("public_repos", 0),
                "followers": user_details.get("followers", 0),
                "monthly_commits": activity["commits"],
                "repositories_contributed": len(activity["repositories"]),
                "repository_list": sorted(list(activity["repositories"])),
                "commit_details": sorted(activity["commit_details"], 
                                       key=lambda x: x["date"], reverse=True),
                "first_commit_date": min(activity["commit_dates"]) if activity["commit_dates"] else None,
                "last_commit_date": max(activity["commit_dates"]) if activity["commit_dates"] else None,
                "active_days": len(set(date[:10] for date in activity["commit_dates"] if date))
            }
            
            enriched_contributors.append(contributor_data)
            time.sleep(0.2)  # Rate limiting for user API calls
        
        # Sort contributors by monthly commits
        enriched_contributors.sort(key=lambda x: x["monthly_commits"], reverse=True)
        
        # Add rankings
        for i, contributor in enumerate(enriched_contributors, 1):
            contributor["rank"] = i
        
        # Generate summary statistics
        total_contributors = len(enriched_contributors)
        active_contributors = [c for c in enriched_contributors if c["monthly_commits"] >= 5]
        very_active_contributors = [c for c in enriched_contributors if c["monthly_commits"] >= 20]
        
        # Company and location analysis
        company_stats = defaultdict(lambda: {"contributors": 0, "commits": 0})
        location_stats = defaultdict(lambda: {"contributors": 0, "commits": 0})
        
        for contributor in enriched_contributors:
            company = contributor.get("company")
            if company:
                company = company.strip().lstrip("@").lower()
                company_stats[company]["contributors"] += 1
                company_stats[company]["commits"] += contributor["monthly_commits"]
            
            location = contributor.get("location")
            if location:
                location = location.strip().lower()
                location_stats[location]["contributors"] += 1
                location_stats[location]["commits"] += contributor["monthly_commits"]
        
        # Most active repositories
        sorted_repos = sorted(repo_activity.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "organization": org_name,
            "analysis_period": "Last 30 days",
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "generated_at": datetime.now().isoformat(),
            "company_filter": company_filter,
            "summary": {
                "total_repositories_analyzed": len(org_repos),
                "total_active_repositories": len([r for r in repo_activity.values() if r > 0]),
                "total_commits": total_commits,
                "total_contributors": total_contributors,
                "active_contributors": len(active_contributors),  # 5+ commits
                "very_active_contributors": len(very_active_contributors),  # 20+ commits
                "average_commits_per_contributor": round(total_commits / total_contributors, 2) if total_contributors > 0 else 0,
                "repositories_with_activity": dict(sorted_repos[:10])
            },
            "contributors": enriched_contributors,
            "company_distribution": dict(sorted(company_stats.items(), 
                                              key=lambda x: x[1]["commits"], reverse=True)),
            "location_distribution": dict(sorted(location_stats.items(), 
                                                key=lambda x: x[1]["commits"], reverse=True)),
            "repository_activity": repo_activity
        }
    
    def print_monthly_analysis(self, analysis: Dict[str, Any]):
        """Print formatted monthly analysis"""
        org_name = analysis.get("organization", "Unknown")
        summary = analysis.get("summary", {})
        company_filter = analysis.get("company_filter")
        
        print(f"\n" + "="*80)
        print(f"MONTHLY CONTRIBUTOR ANALYSIS: {org_name.upper()}")
        if company_filter:
            print(f"FILTERED BY COMPANY: {company_filter.upper()}")
        print(f"PERIOD: {analysis.get('start_date')} to {analysis.get('end_date')}")
        print("="*80)
        
        print(f"📊 SUMMARY STATISTICS")
        print(f"Total Repositories Analyzed: {summary.get('total_repositories_analyzed', 0):,}")
        print(f"Active Repositories (with commits): {summary.get('total_active_repositories', 0):,}")
        print(f"Total Commits: {summary.get('total_commits', 0):,}")
        print(f"Total Contributors: {summary.get('total_contributors', 0):,}")
        print(f"Active Contributors (5+ commits): {summary.get('active_contributors', 0):,}")
        print(f"Very Active Contributors (20+ commits): {summary.get('very_active_contributors', 0):,}")
        print(f"Average Commits per Contributor: {summary.get('average_commits_per_contributor', 0):,.2f}")
        
        # Top repositories by activity
        print(f"\n🏆 MOST ACTIVE REPOSITORIES")
        repo_activity = summary.get("repositories_with_activity", {})
        for repo, commits in list(repo_activity.items())[:10]:
            print(f"  {repo}: {commits:,} commits")
        
        # Company distribution (if not filtering by company)
        if not company_filter:
            print(f"\n🏢 COMPANY DISTRIBUTION")
            company_dist = analysis.get("company_distribution", {})
            for company, stats in list(company_dist.items())[:10]:
                if company:
                    print(f"  {company}: {stats['contributors']} contributors, {stats['commits']:,} commits")
        
        # Location distribution
        print(f"\n🌍 LOCATION DISTRIBUTION")
        location_dist = analysis.get("location_distribution", {})
        for location, stats in list(location_dist.items())[:10]:
            if location:
                print(f"  {location}: {stats['contributors']} contributors, {stats['commits']:,} commits")
        
        # Top contributors
        contributors = analysis.get("contributors", [])
        if contributors:
            print(f"\n👥 TOP CONTRIBUTORS RANKING")
            print("="*100)
            print(f"{'Rank':<5} {'Username':<20} {'Name':<25} {'Commits':<8} {'Repos':<6} {'Days':<5} {'Company':<15}")
            print("-"*100)
            
            for contributor in contributors[:20]:
                rank = contributor.get("rank", 0)
                username = contributor.get("username", "")[:19]
                name = (contributor.get("name") or "")[:24]
                commits = contributor.get("monthly_commits", 0)
                repos = contributor.get("repositories_contributed", 0)
                days = contributor.get("active_days", 0)
                company = (contributor.get("company") or "").strip().lstrip("@")[:14]
                
                print(f"{rank:<5} {username:<20} {name:<25} {commits:<8} {repos:<6} {days:<5} {company:<15}")
            
            # Spotlight on top contributor
            if contributors:
                top = contributors[0]
                print(f"\n🌟 TOP CONTRIBUTOR SPOTLIGHT")
                print(f"Username: @{top.get('username')}")
                print(f"Name: {top.get('name') or 'Not provided'}")
                print(f"Monthly Commits: {top.get('monthly_commits', 0):,}")
                print(f"Repositories: {top.get('repositories_contributed', 0)}")
                print(f"Active Days: {top.get('active_days', 0)}")
                print(f"Company: {top.get('company') or 'Not provided'}")
                print(f"Profile: {top.get('profile_url')}")
                
                print(f"\nRecent Commits:")
                recent_commits = top.get("commit_details", [])[:5]
                for commit in recent_commits:
                    date = commit.get("date", "")[:10]
                    repo = commit.get("repository", "")
                    message = commit.get("message", "")
                    print(f"  {date} [{repo}] {message}")
        else:
            print(f"\nNo contributors found matching the criteria.")
    
    def save_analysis(self, analysis: Dict[str, Any], filename: str):
        """Save analysis to JSON file"""
        with open(filename, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"Monthly analysis saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Monthly GitHub Contributor Analysis")
    parser.add_argument("organization", help="Organization name")
    parser.add_argument("--token", help="GitHub personal access token")
    parser.add_argument("--company", help="Filter contributors by company name")
    parser.add_argument("--type", default="all", 
                       choices=["all", "public", "private", "forks", "sources", "member"],
                       help="Type of repositories to analyze")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--top", type=int, default=20, help="Number of top contributors to display")
    parser.add_argument("--no-summary", action="store_true", help="Don't print summary to console")
    
    args = parser.parse_args()
    
    # Get token from environment if not provided
    token = args.token or os.environ.get("GITHUB_TOKEN")
    
    if not token:
        print("Warning: No GitHub token provided. API rate limits will be lower.")
        print("Set GITHUB_TOKEN environment variable or use --token option.")
    
    analyzer = MonthlyContributorAnalyzer(token)
    
    # Run analysis
    analysis = analyzer.analyze_monthly_contributors(
        args.organization,
        args.type,
        args.company
    )
    
    if analysis:
        # Save to file if specified
        if args.output:
            analyzer.save_analysis(analysis, args.output)
        
        # Print analysis unless disabled
        if not args.no_summary:
            analyzer.print_monthly_analysis(analysis)
    else:
        print("No analysis data generated. Please check the organization name and try again.")


if __name__ == "__main__":
    main()