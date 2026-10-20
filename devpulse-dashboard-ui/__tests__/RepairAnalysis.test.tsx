import { TextEncoder } from 'util';
Object.defineProperty(globalThis, 'TextEncoder', { value: TextEncoder });

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import RepairAnalysis from '../src/components/RepairAnalysis';
import { apiRequest } from '../src/lib/transport';

jest.mock('../src/lib/transport', () => ({ apiRequest: jest.fn() }));
const request = apiRequest as jest.Mock;
const workspace = {id:'ws',name:'My team',role:'owner'};
const analysis = { id:'run', workspace_id:'ws', created_at:'2026-10-20T06:00:00+00:00', evidence_hash:'abc',
  report:{outcome:'review_required',before_operations:1,after_operations:0,changes:[{operation_ref:'hash',method:'GET',kind:'operation_removed',compatibility:'breaking'}], limitations:['No patch or test execution performed']} };

beforeEach(() => request.mockReset());

it('submits consented real inputs and displays evidence without claiming a repair', async () => {
  request.mockResolvedValueOnce({workspaces:[workspace]}).mockResolvedValueOnce({analyses:[]}).mockResolvedValueOnce({analysis});
  render(<RepairAnalysis />);
  await screen.findByText('No analyses in this workspace yet.');
  fireEvent.change(screen.getByLabelText('Previous contract'), {target:{value:'{"openapi":"3.0.3","paths":{}}'}});
  fireEvent.change(screen.getByLabelText('Current contract'), {target:{value:'{"openapi":"3.0.3","paths":{}}'}});
  const submit = screen.getByRole('button',{name:'Analyze contracts'});
  expect(submit).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(submit);
  await screen.findByText('Human review required');
  const body = JSON.parse(request.mock.calls[2][1].body);
  expect(body).toMatchObject({workspace_id:'ws',consent:true,before:{openapi:'3.0.3'}});
  expect(screen.getByText('No patch or test execution performed')).toBeInTheDocument();
  expect(screen.getByLabelText('Previous contract')).toHaveValue('');
});

it('shows viewer access and failed history loading honestly', async () => {
  request.mockResolvedValueOnce({workspaces:[{...workspace,role:'viewer'}]}).mockRejectedValueOnce(new Error('503'));
  render(<RepairAnalysis />);
  await screen.findByText('Your workspace role has read-only access.');
  await screen.findByRole('alert');
  expect(screen.queryByRole('button',{name:'Analyze contracts'})).not.toBeInTheDocument();
});

it('creates a real workspace for a new account', async () => {
  request.mockResolvedValueOnce({workspaces:[]}).mockResolvedValueOnce({id:'ws',name:'New workspace'}).mockResolvedValueOnce({analyses:[]});
  render(<RepairAnalysis />);
  await screen.findByText('Create your first workspace to begin.');
  fireEvent.change(screen.getByLabelText('Workspace name'),{target:{value:'New workspace'}});
  fireEvent.click(screen.getByRole('button',{name:'Create workspace'}));
  await screen.findByText('No analyses in this workspace yet.');
  await waitFor(() => expect(request).toHaveBeenCalledWith('/api/teams/workspaces',expect.objectContaining({method:'POST'})));
});
