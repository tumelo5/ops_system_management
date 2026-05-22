import AddClientForm from "./components/warehouse/AddClientForm";
import HRPage from "./pages/HRPage";

function App() {
  return (
    <div>
      <AddClientForm />
      <HRPage />

    </div>
  );
}

export default App;



// import { BrowserRouter, Routes, Route } from "react-router-dom";
// import ClientPage from "./pages/ClientPage";
// import HRPage from "./pages/HRPage";

// function App() {
//   return (
//     <BrowserRouter>
//       <Routes>
//         <Route path="/warehouse" element={<ClientPage />} />
//         <Route path="/hr"        element={<HRPage />} />
//       </Routes>
//     </BrowserRouter>
//   );
// }

// export default App;