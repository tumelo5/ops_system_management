import React from 'react';
import ReactDOM from 'react-dom/client';
import AddClientForm from './components/warehouse/AddClientForm'; 
import BulkAddClientForm from './components/warehouse/BulkAddClientForm'; 


const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    {/* <AddClientForm /> */}
    <BulkAddClientForm />
  </React.StrictMode>
);

