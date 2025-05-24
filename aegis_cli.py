import click
import json

# Assuming backend modules are in the same directory or PYTHONPATH
import did_system
import project_management
import contribution_workflow
import ipfs_storage # Though not directly called by CLI, its init might print messages

# Helper to pretty print JSON
def print_json(data):
    if data is not None:
        click.echo(json.dumps(data, indent=2, sort_keys=True))
    else:
        click.echo("No data to display.")

@click.group()
def cli():
    """Aegis Forge Command Line Interface."""
    # Check IPFS connection early if possible, or let individual commands fail.
    # For now, let ipfs_storage.py handle its initial connection message.
    if ipfs_storage.client is None:
        click.secho("Warning: IPFS daemon does not seem to be running. Some commands will fail.", fg="yellow")
    pass

# --- DID Commands ---
@cli.group('did')
def did_group():
    """Manage Decentralized Identifiers (DIDs)."""
    pass

@did_group.command('create')
@click.option('--nickname', help="Optional nickname for the DID.")
def did_create(nickname):
    """Creates a new DID."""
    try:
        did_string, did_data = did_system.create_did(nickname=nickname)
        click.secho(f"DID created successfully!", fg="green")
        print_json(did_data)
    except Exception as e:
        click.secho(f"Error creating DID: {e}", fg="red")

@did_group.command('list')
def did_list():
    """Lists all created DIDs."""
    try:
        dids = did_system.list_dids()
        if dids:
            print_json(dids)
        else:
            click.echo("No DIDs found.")
    except Exception as e:
        click.secho(f"Error listing DIDs: {e}", fg="red")

@did_group.command('show')
@click.argument('did_string')
def did_show(did_string):
    """Shows details for a specific DID."""
    try:
        did_data = did_system.get_did(did_string)
        if did_data:
            print_json(did_data)
        else:
            click.secho(f"DID '{did_string}' not found.", fg="yellow")
    except Exception as e:
        click.secho(f"Error showing DID '{did_string}': {e}", fg="red")

# --- Project Commands ---
@cli.group('project')
def project_group():
    """Manage Projects."""
    pass

@project_group.command('create')
@click.argument('project_name')
@click.option('--owner-did', required=True, help="The DID of the project owner.")
@click.option('--supply', type=int, default=1000000, show_default=True, help="Initial token supply for the project.")
def project_create(project_name, owner_did, supply):
    """Creates a new project."""
    try:
        project_data = project_management.create_project(project_name, owner_did, token_supply=supply)
        if project_data:
            click.secho(f"Project '{project_name}' created successfully!", fg="green")
            print_json(project_data)
        else:
            # create_project prints its own errors, but we add a generic one here if None is returned.
            click.secho(f"Failed to create project '{project_name}'. See backend logs for details.", fg="red")
    except Exception as e:
        click.secho(f"Error creating project: {e}", fg="red")

@project_group.command('list')
def project_list():
    """Lists all projects."""
    try:
        projects = project_management.list_projects()
        if projects:
            print_json(projects)
        else:
            click.echo("No projects found.")
    except Exception as e:
        click.secho(f"Error listing projects: {e}", fg="red")

@project_group.command('show')
@click.argument('project_id')
def project_show(project_id):
    """Shows details for a specific project."""
    try:
        project_data = project_management.get_project(project_id)
        if project_data:
            print_json(project_data)
        else:
            click.secho(f"Project '{project_id}' not found.", fg="yellow")
    except Exception as e:
        click.secho(f"Error showing project '{project_id}': {e}", fg="red")

@project_group.command('balance')
@click.argument('project_id')
@click.argument('did_string')
def project_balance(project_id, did_string):
    """Shows token balance of a DID for a specific project."""
    try:
        project_data = project_management.get_project(project_id)
        if not project_data:
            click.secho(f"Project '{project_id}' not found.", fg="yellow")
            return

        if not did_system.get_did(did_string): # Validate DID existence
            click.secho(f"DID '{did_string}' not found.", fg="yellow")
            return

        token_ledger = project_data.get("token_ledger", {})
        balance = token_ledger.get(did_string, 0)
        click.echo(f"Token balance for DID '{did_string}' in project '{project_id}': {balance} {project_data.get('token_name', 'tokens')}")
    except Exception as e:
        click.secho(f"Error getting balance for project '{project_id}', DID '{did_string}': {e}", fg="red")


# --- Contribution Commands ---
@cli.group('contribution')
def contribution_group():
    """Manage Contributions to Projects."""
    pass

@contribution_group.command('submit')
@click.argument('project_id')
@click.option('--contributor-did', required=True, help="The DID of the contributor.")
@click.option('--title', required=True, help="Title of the contribution.")
@click.option('--description', required=True, help="Description of the contribution.")
@click.option('--file', 'content_file_path', required=True, type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to the file containing the contribution content.")
def contribution_submit(project_id, contributor_did, title, description, content_file_path):
    """Submits a new contribution proposal to a project."""
    try:
        proposal_id = contribution_workflow.submit_contribution(
            project_id, contributor_did, title, description, content_file_path
        )
        if proposal_id:
            click.secho(f"Contribution '{title}' submitted successfully!", fg="green")
            click.echo(f"Proposal ID: {proposal_id}")
            # Optionally show the full proposal data:
            # proposal_data = contribution_workflow.get_contribution(proposal_id)
            # print_json(proposal_data)
        else:
            click.secho(f"Failed to submit contribution for project '{project_id}'. See backend logs.", fg="red")
    except Exception as e:
        click.secho(f"Error submitting contribution: {e}", fg="red")

@contribution_group.command('list')
@click.option('--project-id', help="Optional project ID to filter contributions.")
def contribution_list(project_id):
    """Lists all contributions, or those for a specific project."""
    try:
        if project_id:
            contributions = contribution_workflow.list_contributions_for_project(project_id)
            if not contributions:
                 click.echo(f"No contributions found for project '{project_id}'.")
                 return
        else:
            contributions = contribution_workflow.list_all_contributions()
            if not contributions:
                click.echo("No contributions found in the system.")
                return
        
        print_json(contributions)
    except Exception as e:
        click.secho(f"Error listing contributions: {e}", fg="red")

@contribution_group.command('show')
@click.argument('proposal_id')
def contribution_show(proposal_id):
    """Shows details for a specific contribution proposal."""
    try:
        proposal_data = contribution_workflow.get_contribution(proposal_id)
        if proposal_data:
            print_json(proposal_data)
        else:
            click.secho(f"Contribution proposal '{proposal_id}' not found.", fg="yellow")
    except Exception as e:
        click.secho(f"Error showing contribution proposal '{proposal_id}': {e}", fg="red")

@contribution_group.command('review')
@click.argument('proposal_id')
@click.option('--reviewer-did', required=True, help="The DID of the reviewer (must be project owner).")
@click.option('--status', required=True, type=click.Choice(['approved', 'rejected'], case_sensitive=False), help="New status for the proposal.")
@click.option('--reward', type=int, default=0, show_default=True, help="Token reward amount if approved.")
def contribution_review(proposal_id, reviewer_did, status, reward):
    """Reviews a contribution proposal."""
    try:
        success = contribution_workflow.review_contribution(proposal_id, reviewer_did, status, reward)
        if success:
            click.secho(f"Contribution proposal '{proposal_id}' reviewed successfully. New status: {status}.", fg="green")
            # Optionally show the updated proposal data:
            # proposal_data = contribution_workflow.get_contribution(proposal_id)
            # print_json(proposal_data)
        else:
            click.secho(f"Failed to review contribution proposal '{proposal_id}'. See backend logs.", fg="red")
    except Exception as e:
        click.secho(f"Error reviewing contribution: {e}", fg="red")

if __name__ == '__main__':
    cli()
