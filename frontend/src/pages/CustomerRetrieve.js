import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function CustomerRetrieve() {
  const { vehicleId } = useParams();
  const [vehicle, setVehicle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchVehicle();
  }, [vehicleId]);

  const fetchVehicle = async () => {
    try {
      const res = await axios.get(`${API}/retrieve/${vehicleId}`);
      setVehicle(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Vehicle not found");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      const res = await axios.post(`${API}/retrieve/${vehicleId}/confirm`);
      setResult(res.data);
    } catch (err) {
      setResult({
        status: "error",
        message: err.response?.data?.detail || "Something went wrong. Please try again.",
      });
    } finally {
      setConfirming(false);
    }
  };

  if (loading) {
    return (
      <div className="retrieve-page" data-testid="retrieve-loading">
        <div className="retrieve-card">
          <div className="retrieve-spinner" />
          <p style={{ color: "#a1a1aa", marginTop: 16 }}>Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="retrieve-page" data-testid="retrieve-error">
        <div className="retrieve-card">
          <div className="retrieve-icon retrieve-icon-error">!</div>
          <h2 style={{ color: "#fff", margin: "16px 0 8px" }}>Not Found</h2>
          <p style={{ color: "#a1a1aa" }}>{error}</p>
        </div>
      </div>
    );
  }

  // Already checked out
  if (vehicle?.status === "checked_out") {
    return (
      <div className="retrieve-page" data-testid="retrieve-checked-out">
        <div className="retrieve-card">
          <div className="retrieve-icon retrieve-icon-done">&#10003;</div>
          <h2 style={{ color: "#fff", margin: "16px 0 8px" }}>Already Collected</h2>
          <p style={{ color: "#a1a1aa" }}>
            Your vehicle <strong>{vehicle.license_plate}</strong> has already been checked out.
          </p>
        </div>
      </div>
    );
  }

  // Result after confirming
  if (result) {
    const isSuccess = result.status === "open";
    const isPending = result.status === "pending_payment";
    return (
      <div className="retrieve-page" data-testid="retrieve-result">
        <div className="retrieve-card">
          <div className={`retrieve-icon ${isSuccess ? "retrieve-icon-done" : isPending ? "retrieve-icon-pending" : "retrieve-icon-error"}`}>
            {isSuccess ? "✓" : isPending ? "₹" : "!"}
          </div>
          <h2 style={{ color: "#fff", margin: "16px 0 8px" }}>
            {isSuccess ? "Request Confirmed!" : isPending ? "Payment Required" : "Notice"}
          </h2>
          <p style={{ color: "#a1a1aa", lineHeight: 1.5 }}>{result.message}</p>
        </div>
      </div>
    );
  }

  // Active ticket already exists
  if (vehicle?.active_ticket_status) {
    const statusLabels = {
      open: "Your retrieval request is active. A valet will claim it shortly.",
      claimed: "A valet has claimed your request and is on the way to your car.",
      en_route: "Your car is being brought to the pickup area.",
      arrived: "Your car is at the entrance! Please come to the pickup area.",
      pending_payment: "Your retrieval is pending payment. Please complete payment to proceed.",
    };
    return (
      <div className="retrieve-page" data-testid="retrieve-active-ticket">
        <div className="retrieve-card">
          <div className="retrieve-icon retrieve-icon-active">&#8635;</div>
          <h2 style={{ color: "#fff", margin: "16px 0 8px" }}>Request In Progress</h2>
          <p className="retrieve-plate">{vehicle.license_plate}</p>
          <p style={{ color: "#a1a1aa", lineHeight: 1.5 }}>
            {statusLabels[vehicle.active_ticket_status] || "Your request is being processed."}
          </p>
        </div>
      </div>
    );
  }

  // Main retrieval confirmation
  return (
    <div className="retrieve-page" data-testid="retrieve-confirm-page">
      <div className="retrieve-card">
        <div className="retrieve-brand">PARKARO</div>
        <p style={{ color: "#71717a", fontSize: 12, letterSpacing: 2, marginBottom: 24 }}>
          {vehicle.client_name?.toUpperCase()}
        </p>

        <div className="retrieve-plate-box" data-testid="retrieve-license-plate">
          {vehicle.license_plate}
        </div>

        {vehicle.tag_number && (
          <p style={{ color: "#a1a1aa", fontSize: 14, marginTop: 8 }}>
            Tag #{vehicle.tag_number}
          </p>
        )}

        {vehicle.valet_fee > 0 && (
          <div className="retrieve-fee" data-testid="retrieve-fee-info">
            <span style={{ color: "#a1a1aa" }}>Valet Fee</span>
            <span style={{ color: "#fff", fontWeight: 700, fontSize: 20 }}>
              Rs.{vehicle.valet_fee}
            </span>
          </div>
        )}

        <button
          className="retrieve-btn"
          onClick={handleConfirm}
          disabled={confirming}
          data-testid="retrieve-confirm-button"
        >
          {confirming ? "Requesting..." : "Get My Car"}
        </button>

        <p style={{ color: "#52525b", fontSize: 12, marginTop: 16 }}>
          A valet will bring your car to the pickup area
        </p>
      </div>
    </div>
  );
}
