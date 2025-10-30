import { BrowserRouter as Router, Routes, Route } from "react-router";
import SignIn from "./pages/AuthPages/SignIn";
import SignUp from "./pages/AuthPages/SignUp";
import NotFound from "./pages/OtherPage/NotFound";
import UserProfiles from "./pages/UserProfiles";
import Videos from "./pages/UiElements/Videos";
import Images from "./pages/UiElements/Images";
import Alerts from "./pages/UiElements/Alerts";
import Badges from "./pages/UiElements/Badges";
import Avatars from "./pages/UiElements/Avatars";
import Buttons from "./pages/UiElements/Buttons";
import LineChart from "./pages/Charts/LineChart";
import BarChart from "./pages/Charts/BarChart";
import BasicTables from "./pages/Tables/BasicTables";
import FormElements from "./pages/Forms/FormElements";
import Blank from "./pages/Blank";
import Iaassistant from "./pages/iaassistant";
import Task_assistant from "./pages/Task_assistant";
import WorkAllignement from "./pages/Workallignement";
import Adminpanel from "./pages/Adminpanel";
import AppLayout from "./layout/AppLayout";
import { ScrollToTop } from "./components/common/ScrollToTop";
import Home from "./pages/Dashboard/Home";
import RTdashboard from "./pages/Dashboard/RTdashboard";
import Dailyreports from "./pages/Dashboard/Dailyreports";
import Requests from "./pages/Requests";
import Myactivity from "./pages/Myactivity";
import ProtectedRoute from "./ProtectedRoute";

export default function App() {
  return (
    <Router>
      <ScrollToTop />
      <Routes>
        {/* Dashboard Layout */}
        <Route element={<AppLayout />}>
          {/* 🔓 Home (both roles) */}
          <Route
            index
            path="/Dashboard"
            element={
              <ProtectedRoute allowedRoles={["admin", "user"]}>
                <Home />
              </ProtectedRoute>
            }
          />

          {/* 🔓 Normal user dashboards */}
          <Route
            path="/RTdashboard"
            element={
              <ProtectedRoute allowedRoles={["admin", "user"]}>
                <RTdashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/Dailyreports"
            element={
              <ProtectedRoute allowedRoles={["admin", "user"]}>
                <Dailyreports />
              </ProtectedRoute>
            }
          />

          <Route
            path="/iaassistant"
            element={
              <ProtectedRoute allowedRoles={["admin", "user"]}>
                <Iaassistant />
              </ProtectedRoute>
            }
          />

          <Route
            path="/Myactivity"
            element={
              <ProtectedRoute allowedRoles={["admin", "user"]}>
                <Myactivity />
              </ProtectedRoute>
            }
          />

          <Route
            path="/profile"
            element={
              <ProtectedRoute allowedRoles={["admin", "user"]}>
                <UserProfiles />
              </ProtectedRoute>
            }
          />

          {/* 🔐 Admin-only */}
          <Route
            path="/Adminpanel"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <Adminpanel />
              </ProtectedRoute>
            }
          />

          {/* Extra pages (only admin by default) */}
          <Route
            path="/blank"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <Blank />
              </ProtectedRoute>
            }
          />
          <Route
            path="/Task_assistant"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <Task_assistant />
              </ProtectedRoute>
            }
          />
          <Route
            path="/WorkAllignement"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <WorkAllignement />
              </ProtectedRoute>
            }
          />
          <Route
            path="/Requests"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <Requests />
              </ProtectedRoute>
            }
          />

          {/* Forms, Tables, UI, Charts — keep admin-only */}
          <Route
            path="/form-elements"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <FormElements />
              </ProtectedRoute>
            }
          />
          <Route
            path="/basic-tables"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <BasicTables />
              </ProtectedRoute>
            }
          />
          <Route
            path="/alerts"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <Alerts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/avatars"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <Avatars />
              </ProtectedRoute>
            }
          />
          <Route
            path="/badge"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <Badges />
              </ProtectedRoute>
            }
          />
          <Route
            path="/buttons"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <Buttons />
              </ProtectedRoute>
            }
          />
          <Route
            path="/images"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <Images />
              </ProtectedRoute>
            }
          />
          <Route
            path="/videos"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <Videos />
              </ProtectedRoute>
            }
          />
          <Route
            path="/line-chart"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <LineChart />
              </ProtectedRoute>
            }
          />
          <Route
            path="/bar-chart"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <BarChart />
              </ProtectedRoute>
            }
          />
        </Route>

        {/* Auth Layout */}
        <Route path="/" element={<SignIn />} />
        <Route path="/set-password" element={<SignUp />} />

        {/* Unauthorized */}
        {/* Fallback Route */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}
