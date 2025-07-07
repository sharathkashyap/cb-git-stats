#!/usr/bin/env python3
"""
GitHub Repository Stats Generator
Collects and analyzes statistics from multiple GitHub repositories
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import argparse
import os

class GitHubStatsCollector:
    def __init__(self, token: str = None):
        """
        Initialize the GitHub stats collector
        
        Args:
            token: GitHub personal access token for authenticated requests
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Stats-Collector"
        }
        
        if token:
            self.headers["Authorization"] = f"token {token}"
    
    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get basic repository information"""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching repo {owner}/{repo}: {response.status_code}")
            return None
    
    def get_repo_stats(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get comprehensive repository statistics"""
        print(f"Fetching stats for {owner}/{repo}...")
        
        # Get basic repo info
        repo_info = self.get_repo_info(owner, repo)
        if not repo_info:
            return None
        
        stats = {
            "repository": f"{owner}/{repo}",
            "name": repo_info.get("name"),
            "description": repo_info.get("description"),
            "created_at": repo_info.get("created_at"),
            "updated_at": repo_info.get("updated_at"),
            "language": repo_info.get("language"),
            "stars": repo_info.get("stargazers_count", 0),
            "forks": repo_info.get("forks_count", 0),
            "watchers": repo_info.get("watchers_count", 0),
            "open_issues": repo_info.get("open_issues_count", 0),
            "size": repo_info.get("size", 0),  # KB
            "default_branch": repo_info.get("default_branch"),
            "is_private": repo_info.get("private", False),
            "has_wiki": repo_info.get("has_wiki", False),
            "has_pages": repo_info.get("has_pages", False),
            "archived": repo_info.get("archived", False),
            "disabled": repo_info.get("disabled", False)
        }
        
        # Get additional stats
        stats.update(self.get_commit_stats(owner, repo))
        stats.update(self.get_contributor_stats(owner, repo))
        stats.update(self.get_release_stats(owner, repo))
        stats.update(self.get_language_stats(owner, repo))
        
        return stats
    
    def get_commit_stats(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get commit statistics"""
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"
        params = {"per_page": 1}
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            # Get total commits from Link header
            link_header = response.headers.get("Link", "")
            total_commits = 0
            
            if "last" in link_header:
                # Extract last page number
                import re
                match = re.search(r'page=(\d+)>; rel="last"', link_header)
                if match:
                    total_commits = int(match.group(1))
            else:
                # If no pagination, count actual commits
                commits_response = requests.get(
                    f"{self.base_url}/repos/{owner}/{repo}/commits",
                    headers=self.headers,
                    params={"per_page": 100}
                )
                if commits_response.status_code == 200:
                    total_commits = len(commits_response.json())
            
            return {"total_commits": total_commits}
        
        return {"total_commits": 0}
    
    def get_contributor_stats(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get contributor statistics"""
        url = f"{self.base_url}/repos/{owner}/{repo}/contributors"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            contributors = response.json()
            return {
                "total_contributors": len(contributors),
                "top_contributors": [
                    {
                        "login": contrib.get("login"),
                        "contributions": contrib.get("contributions", 0)
                    }
                    for contrib in contributors[:5]  # Top 5 contributors
                ]
            }
        
        return {"total_contributors": 0, "top_contributors": []}
    
    def get_release_stats(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get release statistics"""
        url = f"{self.base_url}/repos/{owner}/{repo}/releases"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            releases = response.json()
            return {
                "total_releases": len(releases),
                "latest_release": releases[0].get("tag_name") if releases else None,
                "latest_release_date": releases[0].get("published_at") if releases else None
            }
        
        return {"total_releases": 0, "latest_release": None, "latest_release_date": None}
    
    def get_language_stats(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get programming language statistics"""
        url = f"{self.base_url}/repos/{owner}/{repo}/languages"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            languages = response.json()
            total_bytes = sum(languages.values())
            
            language_percentages = {}
            for lang, bytes_count in languages.items():
                percentage = (bytes_count / total_bytes) * 100 if total_bytes > 0 else 0
                language_percentages[lang] = round(percentage, 2)
            
            return {
                "languages": language_percentages,
                "primary_language": max(language_percentages.keys(), 
                                     key=language_percentages.get) if language_percentages else None
            }
        
        return {"languages": {}, "primary_language": None}
    
    def generate_summary(self, all_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics across all repositories"""
        total_stats = {
            "total_repositories": len(all_stats),
            "total_stars": sum(repo.get("stars", 0) for repo in all_stats),
            "total_forks": sum(repo.get("forks", 0) for repo in all_stats),
            "total_commits": sum(repo.get("total_commits", 0) for repo in all_stats),
            "total_contributors": sum(repo.get("total_contributors", 0) for repo in all_stats),
            "total_releases": sum(repo.get("total_releases", 0) for repo in all_stats),
            "total_size_kb": sum(repo.get("size", 0) for repo in all_stats)
        }
        
        # Language distribution
        all_languages = {}
        for repo in all_stats:
            languages = repo.get("languages", {})
            for lang, percentage in languages.items():
                if lang not in all_languages:
                    all_languages[lang] = []
                all_languages[lang].append(percentage)
        
        # Calculate average percentages
        language_averages = {}
        for lang, percentages in all_languages.items():
            language_averages[lang] = round(sum(percentages) / len(percentages), 2)
        
        total_stats["language_distribution"] = language_averages
        
        return total_stats
    
    def collect_stats(self, repositories: List[str]) -> Dict[str, Any]:
        """
        Collect statistics for multiple repositories
        
        Args:
            repositories: List of repository names in format "owner/repo"
        
        Returns:
            Dictionary containing all statistics
        """
        all_stats = []
        
        for repo_name in repositories:
            if "/" not in repo_name:
                print(f"Invalid repository format: {repo_name}. Use 'owner/repo' format.")
                continue
            
            owner, repo = repo_name.split("/", 1)
            stats = self.get_repo_stats(owner, repo)
            
            if stats:
                all_stats.append(stats)
            
            # Rate limiting - be nice to GitHub API
            time.sleep(1)
        
        summary = self.generate_summary(all_stats)
        
        return {
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "repositories": all_stats
        }
    
    def save_to_file(self, stats: Dict[str, Any], filename: str = "github_stats.json"):
        """Save statistics to a JSON file"""
        with open(filename, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"Statistics saved to {filename}")
    
    def get_organization_repos(self, org_name: str, repo_type: str = "all") -> List[str]:
        """
        Get all repositories from a GitHub organization
        
        Args:
            org_name: Organization name
            repo_type: Type of repositories to fetch ('all', 'public', 'private', 'forks', 'sources', 'member')
        
        Returns:
            List of repository names in 'owner/repo' format
        """
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
                if not page_repos:  # No more repos
                    break
                
                for repo in page_repos:
                    repos.append(f"{org_name}/{repo['name']}")
                
                page += 1
                time.sleep(0.5)  # Rate limiting
            else:
                print(f"Error fetching organization repos: {response.status_code}")
                break
        
        print(f"Found {len(repos)} repositories in {org_name}")
        return repos
    
    def rank_repos_by_commits(self, repositories: List[str]) -> List[Dict[str, Any]]:
        """
        Rank repositories by commit count
        
        Args:
            repositories: List of repository names in format "owner/repo"
        
        Returns:
            List of dictionaries with repository stats, sorted by commit count
        """
        print("Ranking repositories by commit count...")
        
        repo_stats = []
        
        for repo_name in repositories:
            if "/" not in repo_name:
                print(f"Invalid repository format: {repo_name}. Use 'owner/repo' format.")
                continue
            
            owner, repo = repo_name.split("/", 1)
            
            # Get basic repo info and commit stats
            repo_info = self.get_repo_info(owner, repo)
            if not repo_info:
                continue
            
            commit_stats = self.get_commit_stats(owner, repo)
            
            repo_data = {
                "repository": repo_name,
                "name": repo_info.get("name"),
                "description": repo_info.get("description"),
                "language": repo_info.get("language"),
                "stars": repo_info.get("stargazers_count", 0),
                "forks": repo_info.get("forks_count", 0),
                "total_commits": commit_stats.get("total_commits", 0),
                "created_at": repo_info.get("created_at"),
                "updated_at": repo_info.get("updated_at"),
                "size": repo_info.get("size", 0),
                "archived": repo_info.get("archived", False)
            }
            
            repo_stats.append(repo_data)
            
            # Rate limiting
            time.sleep(1)
        
        # Sort by commit count (descending)
        ranked_repos = sorted(repo_stats, key=lambda x: x.get("total_commits", 0), reverse=True)
        
        # Add ranking position
        for i, repo in enumerate(ranked_repos, 1):
            repo["rank"] = i
        
        return ranked_repos
    
    def print_commit_ranking(self, ranked_repos: List[Dict[str, Any]], top_n: int = 10):
        """Print formatted commit ranking"""
        print("\n" + "="*80)
        print("REPOSITORY RANKING BY COMMITS")
        print("="*80)
        print(f"{'Rank':<5} {'Repository':<35} {'Commits':<8} {'Stars':<8} {'Language':<15}")
        print("-"*80)
        
        for repo in ranked_repos[:top_n]:
            rank = repo.get("rank", 0)
            name = repo.get("repository", "")[:34]  # Truncate if too long
            commits = repo.get("total_commits", 0)
            stars = repo.get("stars", 0)
            language = repo.get("language") or "N/A"
            language = language[:14] if language else "N/A"
            
            print(f"{rank:<5} {name:<35} {commits:<8,} {stars:<8,} {language:<15}")
        
        if len(ranked_repos) > top_n:
            print(f"\n... and {len(ranked_repos) - top_n} more repositories")
    
    def generate_org_commit_report(self, org_name: str, repo_type: str = "all", 
                                 output_file: str = None) -> Dict[str, Any]:
        """
        Generate a comprehensive commit-based report for an organization
        
        Args:
            org_name: Organization name
            repo_type: Type of repositories to analyze
            output_file: Optional file to save the report
        
        Returns:
            Dictionary containing the complete report
        """
        # Get all organization repositories
        org_repos = self.get_organization_repos(org_name, repo_type)
        
        if not org_repos:
            print(f"No repositories found for organization: {org_name}")
            return {}
        
        # Rank repositories by commits
        ranked_repos = self.rank_repos_by_commits(org_repos)
        
        # Generate summary statistics
        total_commits = sum(repo.get("total_commits", 0) for repo in ranked_repos)
        total_stars = sum(repo.get("stars", 0) for repo in ranked_repos)
        total_forks = sum(repo.get("forks", 0) for repo in ranked_repos)
        active_repos = [repo for repo in ranked_repos if not repo.get("archived", False)]
        
        # Language distribution
        language_stats = {}
        for repo in ranked_repos:
            lang = repo.get("language")
            if lang:
                if lang not in language_stats:
                    language_stats[lang] = {"repos": 0, "commits": 0}
                language_stats[lang]["repos"] += 1
                language_stats[lang]["commits"] += repo.get("total_commits", 0)
        
        # Most active repositories (top 10% by commits)
        top_10_percent = max(1, len(ranked_repos) // 10)
        most_active = ranked_repos[:top_10_percent]
        
        report = {
            "organization": org_name,
            "generated_at": datetime.now().isoformat(),
            "repository_type": repo_type,
            "summary": {
                "total_repositories": len(ranked_repos),
                "active_repositories": len(active_repos),
                "archived_repositories": len(ranked_repos) - len(active_repos),
                "total_commits": total_commits,
                "total_stars": total_stars,
                "total_forks": total_forks,
                "average_commits_per_repo": round(total_commits / len(ranked_repos), 2) if ranked_repos else 0,
                "most_active_repos_count": len(most_active),
                "language_distribution": language_stats
            },
            "rankings": {
                "by_commits": ranked_repos,
                "most_active": most_active
            }
        }
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Organization report saved to {output_file}")
        
        return report
    
    def get_contributor_details(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get detailed contributor information for a repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/contributors"
        params = {"per_page": 100}
        
        all_contributors = []
        page = 1
        
        while True:
            params["page"] = page
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                contributors = response.json()
                if not contributors:
                    break
                
                for contrib in contributors:
                    contributor_info = {
                        "login": contrib.get("login"),
                        "id": contrib.get("id"),
                        "contributions": contrib.get("contributions", 0),
                        "type": contrib.get("type", "User"),
                        "repository": f"{owner}/{repo}"
                    }
                    
                    # Get additional user details if it's a user (not a bot)
                    if contrib.get("type") == "User":
                        user_details = self.get_user_details(contrib.get("login"))
                        contributor_info.update(user_details)
                    
                    all_contributors.append(contributor_info)
                
                page += 1
                time.sleep(0.3)  # Rate limiting
            else:
                print(f"Error fetching contributors for {owner}/{repo}: {response.status_code}")
                break
        
        return all_contributors
    
    def get_user_details(self, username: str) -> Dict[str, Any]:
        """Get additional details for a user"""
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
                "created_at": user_data.get("created_at"),
                "updated_at": user_data.get("updated_at")
            }
        
        return {}
    
    def analyze_org_contributors(self, org_name: str, repo_type: str = "all", 
                               min_contributions: int = 1) -> Dict[str, Any]:
        """
        Analyze and rank contributors across an organization
        
        Args:
            org_name: Organization name
            repo_type: Type of repositories to analyze
            min_contributions: Minimum contributions to include a contributor
        
        Returns:
            Dictionary containing contributor analysis
        """
        print(f"Analyzing contributors for organization: {org_name}")
        
        # Get all organization repositories
        org_repos = self.get_organization_repos(org_name, repo_type)
        
        if not org_repos:
            print(f"No repositories found for organization: {org_name}")
            return {}
        
        # Collect contributors from all repositories
        all_contributors = {}
        repo_contributor_count = {}
        
        for repo_name in org_repos:
            print(f"Analyzing contributors in {repo_name}...")
            owner, repo = repo_name.split("/", 1)
            
            repo_contributors = self.get_contributor_details(owner, repo)
            repo_contributor_count[repo_name] = len(repo_contributors)
            
            for contributor in repo_contributors:
                login = contributor.get("login")
                contributions = contributor.get("contributions", 0)
                
                if contributions < min_contributions:
                    continue
                
                if login not in all_contributors:
                    all_contributors[login] = {
                        "login": login,
                        "name": contributor.get("name"),
                        "email": contributor.get("email"),
                        "company": contributor.get("company"),
                        "location": contributor.get("location"),
                        "bio": contributor.get("bio"),
                        "public_repos": contributor.get("public_repos", 0),
                        "followers": contributor.get("followers", 0),
                        "following": contributor.get("following", 0),
                        "created_at": contributor.get("created_at"),
                        "type": contributor.get("type", "User"),
                        "total_contributions": 0,
                        "repositories_contributed": [],
                        "repository_count": 0
                    }
                
                all_contributors[login]["total_contributions"] += contributions
                all_contributors[login]["repositories_contributed"].append({
                    "repository": repo_name,
                    "contributions": contributions
                })
        
        # Calculate repository count for each contributor
        for contributor in all_contributors.values():
            contributor["repository_count"] = len(contributor["repositories_contributed"])
            # Sort repositories by contributions
            contributor["repositories_contributed"].sort(
                key=lambda x: x["contributions"], reverse=True
            )
        
        # Convert to list and sort by total contributions
        contributors_list = list(all_contributors.values())
        contributors_list.sort(key=lambda x: x["total_contributions"], reverse=True)
        
        # Add ranking
        for i, contributor in enumerate(contributors_list, 1):
            contributor["rank"] = i
        
        # Generate summary statistics
        total_contributors = len(contributors_list)
        total_contributions = sum(c["total_contributions"] for c in contributors_list)
        active_contributors = [c for c in contributors_list if c["total_contributions"] >= 10]
        super_contributors = [c for c in contributors_list if c["total_contributions"] >= 100]
        
        # Company analysis
        company_stats = {}
        for contributor in contributors_list:
            company = contributor.get("company")
            if company:
                company = company.strip().lstrip("@").lower()
                if company not in company_stats:
                    company_stats[company] = {"contributors": 0, "contributions": 0}
                company_stats[company]["contributors"] += 1
                company_stats[company]["contributions"] += contributor["total_contributions"]
        
        # Location analysis
        location_stats = {}
        for contributor in contributors_list:
            location = contributor.get("location")
            if location:
                location = location.strip().lower()
                if location not in location_stats:
                    location_stats[location] = {"contributors": 0, "contributions": 0}
                location_stats[location]["contributors"] += 1
                location_stats[location]["contributions"] += contributor["total_contributions"]
        
        return {
            "organization": org_name,
            "generated_at": datetime.now().isoformat(),
            "repository_type": repo_type,
            "summary": {
                "total_repositories_analyzed": len(org_repos),
                "total_contributors": total_contributors,
                "active_contributors": len(active_contributors),  # 10+ contributions
                "super_contributors": len(super_contributors),    # 100+ contributions
                "total_contributions": total_contributions,
                "average_contributions_per_contributor": round(total_contributions / total_contributors, 2) if total_contributors > 0 else 0,
                "repositories_with_contributors": len([r for r in repo_contributor_count.values() if r > 0])
            },
            "contributors": contributors_list,
            "company_distribution": dict(sorted(company_stats.items(), 
                                              key=lambda x: x[1]["contributions"], reverse=True)),
            "location_distribution": dict(sorted(location_stats.items(), 
                                                key=lambda x: x[1]["contributions"], reverse=True)),
            "repository_contributor_counts": repo_contributor_count
        }
    
    def print_contributor_ranking(self, contributors: List[Dict[str, Any]], top_n: int = 20):
        """Print formatted contributor ranking"""
        print("\n" + "="*100)
        print("ORGANIZATION CONTRIBUTOR RANKING")
        print("="*100)
        print(f"{'Rank':<5} {'Username':<20} {'Name':<25} {'Contributions':<13} {'Repos':<6} {'Company':<15}")
        print("-"*100)
        
        for contributor in contributors[:top_n]:
            rank = contributor.get("rank", 0)
            username = contributor.get("login", "")[:19]
            name = (contributor.get("name") or "")[:24]
            contributions = contributor.get("total_contributions", 0)
            repo_count = contributor.get("repository_count", 0)
            company = (contributor.get("company") or "").strip().lstrip("@")[:14]
            
            print(f"{rank:<5} {username:<20} {name:<25} {contributions:<13,} {repo_count:<6} {company:<15}")
        
        if len(contributors) > top_n:
            print(f"\n... and {len(contributors) - top_n} more contributors")
    
    def print_contributor_analysis(self, analysis: Dict[str, Any]):
        """Print comprehensive contributor analysis"""
        org_name = analysis.get("organization", "Unknown")
        summary = analysis.get("summary", {})
        
        print(f"\n" + "="*70)
        print(f"CONTRIBUTOR ANALYSIS: {org_name.upper()}")
        print("="*70)
        print(f"Total Repositories Analyzed: {summary.get('total_repositories_analyzed', 0):,}")
        print(f"Total Contributors: {summary.get('total_contributors', 0):,}")
        print(f"Active Contributors (10+ commits): {summary.get('active_contributors', 0):,}")
        print(f"Super Contributors (100+ commits): {summary.get('super_contributors', 0):,}")
        print(f"Total Contributions: {summary.get('total_contributions', 0):,}")
        print(f"Average Contributions per Contributor: {summary.get('average_contributions_per_contributor', 0):,.2f}")
        
        # Company distribution
        print(f"\nTop Companies by Contributions:")
        company_dist = analysis.get("company_distribution", {})
        for company, stats in list(company_dist.items())[:10]:
            if company:
                print(f"  {company}: {stats['contributors']} contributors, {stats['contributions']:,} contributions")
        
        # Location distribution
        print(f"\nTop Locations by Contributors:")
        location_dist = analysis.get("location_distribution", {})
        for location, stats in list(location_dist.items())[:10]:
            if location:
                print(f"  {location}: {stats['contributors']} contributors, {stats['contributions']:,} contributions")
        
        # Print top contributors
        contributors = analysis.get("contributors", [])
        if contributors:
            self.print_contributor_ranking(contributors, top_n=20)
            
            # Show top contributor details
            if contributors:
                top_contributor = contributors[0]
                print(f"\n🏆 TOP CONTRIBUTOR SPOTLIGHT:")
                print(f"Username: {top_contributor.get('login')}")
                print(f"Name: {top_contributor.get('name') or 'Not provided'}")
                print(f"Total Contributions: {top_contributor.get('total_contributions', 0):,}")
                print(f"Repositories Contributed: {top_contributor.get('repository_count', 0)}")
                print(f"Company: {top_contributor.get('company') or 'Not provided'}")
                print(f"Location: {top_contributor.get('location') or 'Not provided'}")
                print(f"Public Repos: {top_contributor.get('public_repos', 0):,}")
                print(f"Followers: {top_contributor.get('followers', 0):,}")
                
                print(f"\nTop Repositories:")
                top_repos = top_contributor.get("repositories_contributed", [])[:5]
                for repo_contrib in top_repos:
                    repo_name = repo_contrib.get("repository")
                    contributions = repo_contrib.get("contributions")
                    print(f"  {repo_name}: {contributions:,} contributions")

    def print_org_summary(self, report: Dict[str, Any]):
        """Print organization summary"""
        org_name = report.get("organization", "Unknown")
        summary = report.get("summary", {})
        
        print(f"\n" + "="*60)
        print(f"ORGANIZATION ANALYSIS: {org_name.upper()}")
        print("="*60)
        print(f"Total Repositories: {summary.get('total_repositories', 0):,}")
        print(f"Active Repositories: {summary.get('active_repositories', 0):,}")
        print(f"Archived Repositories: {summary.get('archived_repositories', 0):,}")
        print(f"Total Commits: {summary.get('total_commits', 0):,}")
        print(f"Total Stars: {summary.get('total_stars', 0):,}")
        print(f"Total Forks: {summary.get('total_forks', 0):,}")
        print(f"Average Commits per Repo: {summary.get('average_commits_per_repo', 0):,.2f}")
        
        print(f"\nTop Programming Languages by Repository Count:")
        lang_stats = summary.get("language_distribution", {})
        sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1]["repos"], reverse=True)
        for lang, stats in sorted_langs[:10]:
            print(f"  {lang}: {stats['repos']} repos, {stats['commits']:,} commits")
        
        # Print top repositories
        rankings = report.get("rankings", {})
        top_repos = rankings.get("by_commits", [])
        if top_repos:
            self.print_commit_ranking(top_repos, top_n=15)
    
    def print_summary(self, stats: Dict[str, Any]):
        """Print a formatted summary of the statistics"""
        summary = stats.get("summary", {})
        
        print("\n" + "="*50)
        print("GITHUB REPOSITORIES SUMMARY")
        print("="*50)
        print(f"Total Repositories: {summary.get('total_repositories', 0)}")
        print(f"Total Stars: {summary.get('total_stars', 0):,}")
        print(f"Total Forks: {summary.get('total_forks', 0):,}")
        print(f"Total Commits: {summary.get('total_commits', 0):,}")
        print(f"Total Contributors: {summary.get('total_contributors', 0):,}")
        print(f"Total Releases: {summary.get('total_releases', 0):,}")
        print(f"Total Size: {summary.get('total_size_kb', 0):,} KB")
        
        print("\nLanguage Distribution:")
        languages = summary.get("language_distribution", {})
        for lang, percentage in sorted(languages.items(), key=lambda x: x[1], reverse=True):
            print(f"  {lang}: {percentage}%")
        
        print("\nTop Repositories by Stars:")
        repos = stats.get("repositories", [])
        top_repos = sorted(repos, key=lambda x: x.get("stars", 0), reverse=True)[:5]
        for repo in top_repos:
            print(f"  {repo.get('repository')}: {repo.get('stars', 0):,} stars")
        
        # Also show commit ranking if we have commit data
        if repos:
            print("\nTop Repositories by Commits:")
            top_by_commits = sorted(repos, key=lambda x: x.get("total_commits", 0), reverse=True)[:5]
            for repo in top_by_commits:
                print(f"  {repo.get('repository')}: {repo.get('total_commits', 0):,} commits")


def main():
    parser = argparse.ArgumentParser(description="Generate GitHub repository statistics")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Subparser for analyzing specific repositories
    repo_parser = subparsers.add_parser('repos', help='Analyze specific repositories')
    repo_parser.add_argument("repositories", nargs="+", help="Repository names in format 'owner/repo'")
    repo_parser.add_argument("--token", help="GitHub personal access token")
    repo_parser.add_argument("--output", default="github_stats.json", help="Output file name")
    repo_parser.add_argument("--no-summary", action="store_true", help="Don't print summary to console")
    
    # Subparser for organization analysis
    org_parser = subparsers.add_parser('org', help='Analyze GitHub organization by commit ranking')
    org_parser.add_argument("organization", help="Organization name")
    org_parser.add_argument("--token", help="GitHub personal access token")
    org_parser.add_argument("--type", default="all", choices=["all", "public", "private", "forks", "sources", "member"],
                           help="Type of repositories to analyze")
    org_parser.add_argument("--output", help="Output file name for organization report")
    org_parser.add_argument("--top", type=int, default=15, help="Number of top repositories to display")
    org_parser.add_argument("--no-summary", action="store_true", help="Don't print summary to console")
    
    # Subparser for ranking repositories by commits
    rank_parser = subparsers.add_parser('rank', help='Rank repositories by commits')
    rank_parser.add_argument("repositories", nargs="+", help="Repository names in format 'owner/repo'")
    rank_parser.add_argument("--token", help="GitHub personal access token")
    rank_parser.add_argument("--output", help="Output file name for ranking report")
    rank_parser.add_argument("--top", type=int, default=10, help="Number of top repositories to display")
    
    # Subparser for contributor analysis
    contrib_parser = subparsers.add_parser('contributors', help='Analyze and rank contributors in organization')
    contrib_parser.add_argument("organization", help="Organization name")
    contrib_parser.add_argument("--token", help="GitHub personal access token")
    contrib_parser.add_argument("--type", default="all", choices=["all", "public", "private", "forks", "sources", "member"],
                               help="Type of repositories to analyze")
    contrib_parser.add_argument("--min-contributions", type=int, default=1, 
                               help="Minimum contributions to include a contributor")
    contrib_parser.add_argument("--output", help="Output file name for contributor analysis")
    contrib_parser.add_argument("--top", type=int, default=20, help="Number of top contributors to display")
    contrib_parser.add_argument("--no-summary", action="store_true", help="Don't print summary to console")
    
    args = parser.parse_args()
    
    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return
    
    # Try to get token from environment if not provided
    token = args.token or os.environ.get("GITHUB_TOKEN")
    
    if not token:
        print("Warning: No GitHub token provided. API rate limits will be lower.")
        print("Set GITHUB_TOKEN environment variable or use --token option.")
    
    collector = GitHubStatsCollector(token)
    
    if args.command == 'repos':
        # Original repository analysis functionality
        print(f"Collecting stats for {len(args.repositories)} repositories...")
        stats = collector.collect_stats(args.repositories)
        
        # Save to file
        collector.save_to_file(stats, args.output)
        
        # Print summary unless disabled
        if not args.no_summary:
            collector.print_summary(stats)
    
    elif args.command == 'org':
        # Organization analysis with commit ranking
        print(f"Analyzing organization: {args.organization}")
        report = collector.generate_org_commit_report(
            args.organization, 
            args.type, 
            args.output
        )
        
        if report and not args.no_summary:
            collector.print_org_summary(report)
    
    elif args.command == 'rank':
        # Repository ranking by commits
        print(f"Ranking {len(args.repositories)} repositories by commits...")
        ranked_repos = collector.rank_repos_by_commits(args.repositories)
        
        # Save to file if specified
        if args.output:
            ranking_report = {
                "generated_at": datetime.now().isoformat(),
                "total_repositories": len(ranked_repos),
                "rankings": ranked_repos
            }
            with open(args.output, 'w') as f:
                json.dump(ranking_report, f, indent=2)
            print(f"Ranking report saved to {args.output}")
        
        # Print ranking
        collector.print_commit_ranking(ranked_repos, args.top)
    
    elif args.command == 'contributors':
        # Contributor analysis
        print(f"Analyzing contributors for organization: {args.organization}")
        analysis = collector.analyze_org_contributors(
            args.organization,
            args.type,
            args.min_contributions
        )
        
        if analysis:
            # Save to file if specified
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(analysis, f, indent=2)
                print(f"Contributor analysis saved to {args.output}")
            
            # Print analysis unless disabled
            if not args.no_summary:
                collector.print_contributor_analysis(analysis)


if __name__ == "__main__":
    main()