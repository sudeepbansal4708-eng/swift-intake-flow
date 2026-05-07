import { Phone, PhoneOff, Car, MapPin } from 'lucide-react';
import '../App.css';

export default function IncomingCall({ ticket, onAnswer, onDecline }) {
  if (!ticket) return null;

  const plate = ticket.vehicle?.license_plate || 'Unknown';
  const tag = ticket.vehicle?.tag_number;
  const zone = ticket.vehicle?.zone_label;

  return (
    <div className="incoming-call-overlay" data-testid="incoming-call-overlay">
      <div className="incoming-call-container">
        {/* Pulse rings */}
        <div className="call-pulse-ring call-pulse-1" />
        <div className="call-pulse-ring call-pulse-2" />
        <div className="call-pulse-ring call-pulse-3" />

        {/* Car icon */}
        <div className="call-icon-wrapper">
          <Car className="w-10 h-10 text-white" />
        </div>

        {/* Info */}
        <div className="call-info">
          <div className="call-title">RETRIEVAL REQUEST</div>
          <div className="call-plate">{plate}</div>
          {tag && <div className="call-tag">Tag #{tag}</div>}
          {zone && (
            <div className="call-zone">
              <MapPin className="w-3.5 h-3.5 inline mr-1" />
              {zone}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="call-actions">
          <button
            data-testid="call-decline-btn"
            className="call-btn call-btn-decline"
            onClick={onDecline}
          >
            <PhoneOff className="w-7 h-7" />
            <span>Decline</span>
          </button>
          <button
            data-testid="call-answer-btn"
            className="call-btn call-btn-answer"
            onClick={onAnswer}
          >
            <Phone className="w-7 h-7" />
            <span>Claim</span>
          </button>
        </div>
      </div>
    </div>
  );
}
