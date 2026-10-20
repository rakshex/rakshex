import { TextEncoder } from 'util';
Object.defineProperty(globalThis,'TextEncoder',{value:TextEncoder});
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import RepairWorkbench from '../src/components/RepairWorkbench';
import {apiRequest} from '../src/lib/transport';
jest.mock('../src/lib/transport',()=>({apiRequest:jest.fn(),apiFetch:jest.fn()}));
const request=apiRequest as jest.Mock;
const workspace={id:'ws',name:'Team',role:'owner'};
const job={id:'job',status:'validated',patch_hash:'a'.repeat(64),evidence_hash:'b'.repeat(64),created_at:'2026-10-20',report:{repository:'rakshex/rakshex',base_sha:'c'.repeat(40),message:'Failing baseline and passing candidate observed',scope:['client.py'],impacts:[{file:'client.py',line:4,kind:'request_property_rename'}],checks:{accepted:true,before:{status:'failed',tests:1,reason:'completed',output_hash:'before'},after:{status:'passed',tests:1,reason:'completed',output_hash:'after'}},limitations:['Only submitted paths tested']}};
beforeEach(()=>request.mockReset());
it('requires explicit consent and sends real manifest inputs',async()=>{
 request.mockResolvedValueOnce({workspaces:[workspace]}).mockResolvedValueOnce({jobs:[],publication_configured:false}).mockResolvedValueOnce({job:{...job,status:'queued'}}).mockResolvedValue({jobs:[{...job,status:'queued'}],publication_configured:false});
 render(<RepairWorkbench/>);await screen.findByText('No repair jobs in this workspace yet.');
 fireEvent.change(screen.getByLabelText('Repair manifest'),{target:{value:'{"repository":"rakshex/rakshex","files":{"client.py":"pass"}}'}});
 const button=screen.getByRole('button',{name:'Plan repair and queue validation'});expect(button).toBeDisabled();
 fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(button);
 await waitFor(()=>expect(request).toHaveBeenCalledWith('/api/repair-jobs',expect.objectContaining({method:'POST'})));
 const body=JSON.parse(request.mock.calls.find(call=>call[1]?.method==='POST')[1].body);
 expect(body).toMatchObject({workspace_id:'ws',consent:true,files:{'client.py':'pass'}});
 await waitFor(()=>expect(screen.getByLabelText('Repair manifest')).toHaveValue(''));
});
it('requires review of exact patch before publication',async()=>{
 request.mockResolvedValueOnce({workspaces:[workspace]}).mockResolvedValueOnce({jobs:[job],publication_configured:true}).mockResolvedValueOnce({diff:'-old\n+new',patch_hash:job.patch_hash});
 render(<RepairWorkbench/>);await screen.findByText('Baseline: failed');
 const publish=screen.getByRole('button',{name:'Approve draft PR publication'});expect(publish).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Review patch'}));await screen.findByLabelText('Proposed patch');expect(publish).toBeEnabled();
 expect(screen.getByText('Only submitted paths tested')).toBeInTheDocument();
});
it('keeps publication unavailable without a connection and viewer cannot submit',async()=>{
 request.mockResolvedValueOnce({workspaces:[{...workspace,role:'viewer'}]}).mockResolvedValueOnce({jobs:[job],publication_configured:false});
 render(<RepairWorkbench/>);await screen.findByText('Your workspace role can review evidence but cannot submit repairs.');
 expect(screen.queryByRole('button',{name:'Approve draft PR publication'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Plan repair and queue validation'})).not.toBeInTheDocument();
 expect(screen.getByText(/GitHub App publication is not connected/)).toBeInTheDocument();
});
